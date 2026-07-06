"""
Sprint 13 demo: today's 8am locked sample encounter, one per mapped provider.

Runs as Pass 2 of the /config/demo/hydrate flow, after the future-meetings
pass. Each mapped provider gets today's 8am 30-min telehealth appointment
checked out, an encounter with realism fields (POS 10, CPT 99213, ICD-10
Z00.00 problem link), a SOAP + Clinical Notes form populated with the
placeholder note, and a single esign_signatures row on the encounter
(table='form_encounter'). With lock_esign_all enabled in OpenEMR globals,
that one signature locks both the encounter and all attached forms in one
shot — and forms.php's existing isLocked() check hides the "Retrieve Zoom
Note" button so the SE can't accidentally trigger a refetch.

Per-day idempotency: at entry, query for any encounter dated today whose
external_id starts with the 'zlock_' marker. If found, skip the entire
pass and surface the skip in the summary. The button is intentionally
one-and-done per day — re-clicking is a no-op for past notes.

Backlog note: issue_encounter currently links every demo encounter to a
generic Z00.00 problem ("Encounter for general adult medical examination,"
created per-patient on demand). Revisit once real per-specialty note
content lands so the linked problem matches the encounter narrative.
"""

import hashlib
import logging
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import text

from app.extensions import get_openemr_db_engine
from app.models import UserMapping, ZoomAccount
from app.services.audit import write_audit_log
from app.services.openemr.appointments.appointment import (
    generate_future_appointment,
    update_appointment_status,
    upsert_patient_tracker,
)
from app.services.openemr.encounter.sample_notes import (
    DEMO_CPT_CODES,
    DEMO_ICD_PROBLEMS,
    get_care_plan_for_category,
    get_clinical_instructions_for_category,
    get_note_for_category,
)
from app.services.openemr.note import write_note_to_encounter
from app.services.openemr.provider import (
    get_provider_appointments_in_window,
    get_provider_patients,
    get_provider_specialty_categories,
    get_provider_username,
)


logger = logging.getLogger(__name__)


# Today's 8am, 30 minutes
_LOCKED_SLOT_TIME = time(8, 0)
_LOCKED_DURATION_SEC = 1800

# Realism defaults
_POS_TELEHEALTH_AT_HOME = 10
# Sentinel prefix on lists.comments so we can recognize + reuse our demo
# problem rows across seedings. Per-ICD distinction comes from lists.diagnosis;
# this prefix is the LIKE pattern used by reset.sh.
_DEMO_PROBLEM_MARKER_PREFIX = "zoomly_demo_problem"
# Sentinel on patient_data.referrer marking the 17 dedicated demo patients
# (PIDs 151-167) whose Sprint 12 charts already match the diabetes scenario
# in PAST_ENCOUNTER_NOTE. _seed_one_provider prefers this patient over
# get_provider_patients()[0] so the locked encounter narrative + the chart
# state align.
_DEMO_PATIENT_REFERRER_SENTINEL = "Zoomly Demo Past Encounter"
# External ID prefix on form_encounter so the per-day guard can recognize
# our seeded rows and skip re-runs. Kept short because form_encounter.external_id
# is VARCHAR(20) — 'zlock_' + up to 14 chars for the eid fits comfortably.
_DEMO_ENCOUNTER_MARKER_PREFIX = "zlock_"


def seed_past_locked_encounters(account: ZoomAccount, note_text: str | None = None) -> dict:
    """
    For each active mapped provider on the account, seed today's 8am locked
    sample encounter. The "already seeded today" check is per-provider —
    each provider gets at most one demo locked encounter per day, but one
    provider's earlier seed (perhaps via a different Zoom account hydrate)
    does not block other providers.

    Returns a summary dict:
        {
            "past_encounters_created": int,
            "past_encounter_skips": [{"openemr_user_id": str, "reason": str}, ...],
            "past_encounter_errors": [{"openemr_user_id": str, "stage": str, "error": str}, ...],
        }
    """
    summary = {
        "past_encounters_created": 0,
        "past_encounter_skips": [],
        "past_encounter_errors": [],
    }

    mappings = UserMapping.query.filter_by(
        zoom_account_id=account.account_id, is_active=True
    ).all()

    for mapping in mappings:
        _seed_one_provider(account, mapping, note_text, summary)

    return summary


# ---------------------------------------------------------------------------
# Per-provider orchestration
# ---------------------------------------------------------------------------

def _seed_one_provider(
    account: ZoomAccount,
    mapping: UserMapping,
    note_text: str | None,
    summary: dict,
) -> None:
    provider_user_id = int(mapping.openemr_user_id)

    # 0. Per-provider, per-day guard. Earlier versions used a global check
    # that broke multi-account hydration (one account's seed marker
    # short-circuited every later account's seeder). Now scoped to this
    # provider so re-hydrating safely no-ops for providers already seeded
    # today, while still seeding any provider that hasn't been touched.
    if _seed_marker_exists_today_for_provider(provider_user_id):
        _record_skip(summary, account, provider_user_id, "already_seeded_today")
        return

    # 1. Resolve specialty + first category
    categories = get_provider_specialty_categories(provider_user_id)
    if not categories:
        _record_skip(summary, account, provider_user_id, "unknown_specialty")
        return
    category_name = categories[0]

    # 2. Patient — prefer the dedicated demo target whose chart already matches
    # the locked encounter narrative; fall back to the provider's first
    # non-demo patient if the demo seed hasn't been run (e.g. older seed).
    patient = _find_demo_patient_for_provider(provider_user_id)
    if patient is None:
        patients = get_provider_patients(provider_user_id)
        if not patients:
            _record_skip(summary, account, provider_user_id, "no_patients")
            return
        patient = patients[0]

    # 3. Facility + category id lookup
    facility_id = (
        int(mapping.openemr_facility_id)
        if mapping.openemr_facility_id
        else _lookup_provider_facility(provider_user_id)
    )
    category_id = _lookup_category_id(category_name)
    if category_id is None:
        _record_skip(summary, account, provider_user_id, "category_missing_in_openemr")
        return

    # 4. 8am slot — use existing or create
    today = date.today()
    existing = _find_today_8am_appt(provider_user_id, today)
    if existing is None:
        eid = generate_future_appointment(
            zoom_account_id=account.account_id,
            provider_user_id=provider_user_id,
            facility_id=facility_id,
            patient_pid=int(patient["pid"]),
            category_id=category_id,
            category_name=category_name,
            slot_date=today,
            slot_time=_LOCKED_SLOT_TIME,
            duration_seconds=_LOCKED_DURATION_SEC,
            title=category_name,
            status=">",  # Checked Out
        )
        if eid is None:
            _record_error(summary, account, provider_user_id, "create_appointment", "appointment INSERT returned None")
            return
        slot_patient_pid = int(patient["pid"])
    else:
        # Use existing — but check if it's already ours or someone else's
        if existing.get("pc_apptstatus") and existing["pc_apptstatus"] not in ("-", ""):
            # Slot is occupied with something already in-progress / checked out / cancelled
            _record_skip(summary, account, provider_user_id, "8am_slot_occupied")
            return
        eid = existing["pc_eid"]
        slot_patient_pid = int(existing["pc_pid"])
        # Flip the existing pending appointment to Checked Out
        update_appointment_status(eid, ">")

    # 5. Create the locked demo encounter (with realism fields + marker external_id)
    encounter_number = _create_locked_demo_encounter(
        pid=slot_patient_pid,
        provider_id=provider_user_id,
        facility_id=facility_id,
        pc_catid=category_id,
        eid=eid,
        reason=f"Telehealth follow-up: {category_name}",
    )
    if encounter_number is None:
        _record_error(summary, account, provider_user_id, "create_encounter", "encounter INSERT returned None")
        return

    # 5b. Keep patient_tracker.encounter pointed at the new encounter so the
    # Flow Board's Encounter column resolves correctly. Direct DB inserts
    # bypass OpenEMR's PHP path that normally does this.
    upsert_patient_tracker(
        eid=int(eid),
        pid=int(slot_patient_pid),
        apptdate=today,
        appttime=_LOCKED_SLOT_TIME,
        encounter=int(encounter_number),
        original_user="zoomly_demo_past_encounter",
    )

    # 6. Attach SOAP + Clinical Notes per writeback mode
    provider_username = get_provider_username(provider_user_id) or f"user{provider_user_id}"
    note_body = note_text or get_note_for_category(category_name)
    writeback_ok = write_note_to_encounter(
        encounter_number=encounter_number,
        pid=slot_patient_pid,
        provider_id=provider_user_id,
        provider_username=provider_username,
        note_content=note_body,
        note_title=f"Telehealth Visit — {category_name}",
        note_id=f"demo-locked-{encounter_number}",
        note_writeback_mode=account.config.note_writeback_mode,
    )
    if not writeback_ok:
        _record_error(summary, account, provider_user_id, "write_note", "write_note_to_encounter returned False")
        return

    # 7. Attach the supplementary forms a checked-out telehealth encounter
    # would realistically carry — Care Plan + Clinical Instructions. The
    # Patient Encounter Form (a.k.a. Visit Summary in the chart view) is
    # already registered against this encounter inside
    # _create_locked_demo_encounter, so we don't add a separate dictation
    # narrative for that anymore.
    patient_full_name = f"{patient.get('fname', '').strip()} {patient.get('lname', '').strip()}".strip()
    today_pretty = datetime.now(timezone.utc).strftime("%B %d, %Y")
    provider_display_name = mapping.openemr_provider_name or provider_username

    _attach_care_plan_form(
        encounter=encounter_number,
        pid=slot_patient_pid,
        provider_user_id=provider_user_id,
        provider_username=provider_username,
        body=get_care_plan_for_category(
            category_name,
            patient_name=patient_full_name,
            date=today_pretty,
            provider_name=provider_display_name,
        ),
    )
    _attach_clinical_instructions_form(
        encounter=encounter_number,
        pid=slot_patient_pid,
        provider_user_id=provider_user_id,
        provider_username=provider_username,
        body=get_clinical_instructions_for_category(
            category_name,
            patient_name=patient_full_name,
            date=today_pretty,
            provider_name=provider_display_name,
        ),
    )

    # 8. Per-encounter ICD-10 problems (issue_encounter linkages). Each demo
    # problem is per-patient reusable via the sentinel on lists.comments —
    # repeated seedings reuse rows rather than accumulating duplicates.
    list_ids = _find_or_create_demo_problems(slot_patient_pid)
    for list_id in list_ids:
        _link_issue_to_encounter(slot_patient_pid, list_id, encounter_number)

    # 9. CPT billing rows (99214 telehealth + 99457/99458 RPM)
    _insert_billing_rows(slot_patient_pid, encounter_number, provider_user_id)

    # 10. E-sign every attached form (per-form rows for the eSign Log section
    # on each form) plus the encounter-level row (cascades the lock via
    # lock_esign_all=1). Manual eSign in the OpenEMR UI produces both kinds
    # of rows; we match that so each form's "eSign Log" panel renders an
    # entry instead of "No signatures on file".
    _esign_all_attached_forms(encounter_number, provider_user_id)
    _esign_encounter(encounter_number, provider_user_id)

    write_audit_log(
        event_type="demo.past_encounter_seeded",
        success=True,
        zoom_account_id=account.account_id,
        openemr_user_id=str(provider_user_id),
        openemr_patient_id=str(slot_patient_pid),
        openemr_appointment_id=str(eid),
        openemr_encounter_number=str(encounter_number),
        detail={"category_name": category_name, "slot_time": _LOCKED_SLOT_TIME.isoformat()},
    )
    summary["past_encounters_created"] += 1


# ---------------------------------------------------------------------------
# Helpers — OpenEMR DB
# ---------------------------------------------------------------------------

def _seed_marker_exists_today_for_provider(provider_user_id: int) -> bool:
    """
    Per-provider per-day guard query.

    Returns True when a locked demo encounter (external_id LIKE 'zlock_%')
    already exists today for this specific OpenEMR provider. Scoped to the
    provider — earlier versions used a global check and broke multi-account
    hydration (one account's first-run seed marker short-circuited every
    other account's seeder for the rest of the day).
    """
    today = date.today()
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT 1 FROM form_encounter
                WHERE DATE(date) = :today
                  AND external_id LIKE :marker
                  AND provider_id = :provider_id
                LIMIT 1
            """),
            {
                "today": today,
                "marker": f"{_DEMO_ENCOUNTER_MARKER_PREFIX}%",
                "provider_id": int(provider_user_id),
            }
        ).fetchone()
    return row is not None


def _find_today_8am_appt(provider_user_id: int, today: date) -> dict | None:
    """Returns the 8am appointment for this provider today, or None."""
    appts = get_provider_appointments_in_window(provider_user_id, today, today)
    for appt in appts:
        if appt["pc_startTime"] == _LOCKED_SLOT_TIME:
            return appt
    return None


def _find_demo_patient_for_provider(provider_user_id: int) -> dict | None:
    """
    Return the dedicated demo past-encounter patient assigned to this provider,
    or None if no demo patient exists (e.g. seed didn't run the S13-05 block).
    Identified by patient_data.referrer = _DEMO_PATIENT_REFERRER_SENTINEL.
    """
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT pid, fname, lname, DOB, sex
                FROM patient_data
                WHERE providerID = :provider_id
                  AND referrer = :sentinel
                ORDER BY pid
                LIMIT 1
            """),
            {"provider_id": int(provider_user_id), "sentinel": _DEMO_PATIENT_REFERRER_SENTINEL}
        ).fetchone()
    if not row:
        return None
    return {
        "pid": row.pid,
        "fname": row.fname,
        "lname": row.lname,
        "dob": row.DOB.isoformat() if row.DOB else None,
        "sex": row.sex,
    }


def _lookup_provider_facility(provider_user_id: int) -> int:
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT facility_id FROM users WHERE id = :id"),
            {"id": int(provider_user_id)}
        ).fetchone()
    return int(row.facility_id) if row and row.facility_id else 0


def _lookup_category_id(category_name: str) -> int | None:
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = :name AND pc_active = 1 LIMIT 1"),
            {"name": category_name}
        ).fetchone()
    return int(row.pc_catid) if row else None


def _create_locked_demo_encounter(
    *,
    pid: int,
    provider_id: int,
    facility_id: int,
    pc_catid: int,
    eid: int,
    reason: str,
) -> int | None:
    """
    Insert form_encounter with realism fields + demo-marker external_id.
    Returns new encounter number on success, None on failure.
    """
    engine = get_openemr_db_engine()
    today_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d 08:00:00")
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    external_id = f"{_DEMO_ENCOUNTER_MARKER_PREFIX}{eid}"

    try:
        with engine.begin() as conn:
            # Idempotency guard at row level — should never fire because the
            # outer pass-level guard catches re-runs, but cheap to keep.
            existing = conn.execute(
                text("SELECT encounter FROM form_encounter WHERE external_id = :external_id"),
                {"external_id": external_id}
            ).fetchone()
            if existing:
                return existing.encounter

            conn.execute(text("UPDATE sequences SET id = id + 1"))
            encounter_number = conn.execute(text("SELECT id FROM sequences")).scalar()
            if encounter_number is None:
                logger.error(
                    f"past_encounter | sequences table empty when generating encounter for eid={eid}"
                )
                return None

            insert_result = conn.execute(
                text("""
                    INSERT INTO form_encounter (
                        uuid, date, onset_date, pid, encounter,
                        pc_catid, provider_id, supervisor_id, facility_id, billing_facility,
                        class_code, reason, external_id,
                        pos_code, last_level_billed, last_level_closed,
                        discharge_disposition, sensitivity, in_collection
                    ) VALUES (
                        :uuid, :dt, :onset, :pid, :encounter,
                        :pc_catid, :provider_id, :provider_id, :facility_id, :facility_id,
                        'VR', :reason, :external_id,
                        :pos_code, 5, 5,
                        '01', '', 0
                    )
                """),
                {
                    "uuid": uuid.uuid4().bytes,
                    "dt": today_dt,
                    "onset": today_date,
                    "pid": int(pid),
                    "encounter": int(encounter_number),
                    "pc_catid": int(pc_catid),
                    "provider_id": int(provider_id),
                    "facility_id": int(facility_id),
                    "reason": reason,
                    "external_id": external_id,
                    "pos_code": _POS_TELEHEALTH_AT_HOME,
                },
            )

            # Register the encounter itself as a 'newpatient' form attached to
            # the encounter — that's what surfaces the editable Patient Encounter
            # Form (Visit Details / Reason for Visit / Linked Issues) in the
            # encounter view. Direct DB INSERT into form_encounter bypasses the
            # PHP path that would normally do this registration for us.
            form_encounter_id = insert_result.lastrowid
            if form_encounter_id:
                conn.execute(
                    text("""
                        INSERT INTO forms (
                            date, encounter, form_name, form_id, pid, user, groupname,
                            authorized, deleted, formdir, provider_id
                        ) VALUES (
                            :dt, :encounter, 'New Patient Encounter', :form_id, :pid,
                            :user, 'Default', 1, 0, 'newpatient', :provider_id
                        )
                    """),
                    {
                        "dt": today_dt,
                        "encounter": int(encounter_number),
                        "form_id": int(form_encounter_id),
                        "pid": int(pid),
                        "user": str(provider_id),
                        "provider_id": int(provider_id),
                    },
                )
            return int(encounter_number)
    except Exception as e:
        logger.error(
            f"past_encounter | _create_locked_demo_encounter failed eid={eid}: {e}"
        )
        return None


def _find_or_create_demo_problems(pid: int) -> list[int]:
    """
    Return list of lists.id values for the per-patient demo ICD-10 problems,
    creating any that are missing. Each demo problem is identified by its
    diagnosis code (lists.diagnosis = 'ICD10:<code>') and tagged with
    lists.comments = '<marker_prefix>_<code>' so they're (a) recognizable as
    Zoomly demo rows and (b) cleanable by reset.sh via LIKE.

    Reused across seedings — the per-day pass-level guard already prevents
    re-runs same day, but this row-level idempotency means a fresh seed +
    next-day run doesn't create duplicates.
    """
    engine = get_openemr_db_engine()
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    list_ids: list[int] = []
    try:
        with engine.begin() as conn:
            for icd_code, title in DEMO_ICD_PROBLEMS:
                diagnosis = f"ICD10:{icd_code}"
                marker = f"{_DEMO_PROBLEM_MARKER_PREFIX}_{icd_code}"

                existing = conn.execute(
                    text("""
                        SELECT id FROM lists
                        WHERE pid = :pid AND diagnosis = :diagnosis
                          AND comments LIKE :marker_like
                          AND type = 'medical_problem'
                        LIMIT 1
                    """),
                    {"pid": int(pid), "diagnosis": diagnosis,
                     "marker_like": f"{_DEMO_PROBLEM_MARKER_PREFIX}%"},
                ).fetchone()
                if existing:
                    list_ids.append(int(existing.id))
                    continue

                result = conn.execute(
                    text("""
                        INSERT INTO lists (
                            date, type, occurrence, classification,
                            title, comments, activity, pid,
                            diagnosis, begdate
                        ) VALUES (
                            NOW(), 'medical_problem', 0, 0,
                            :title, :marker, 1, :pid,
                            :diagnosis, :today
                        )
                    """),
                    {
                        "title": title,
                        "marker": marker,
                        "pid": int(pid),
                        "diagnosis": diagnosis,
                        "today": today_date,
                    },
                )
                if result.lastrowid:
                    list_ids.append(int(result.lastrowid))
    except Exception as e:
        logger.error(f"past_encounter | _find_or_create_demo_problems failed pid={pid}: {e}")
    return list_ids


def _link_issue_to_encounter(pid: int, list_id: int, encounter: int) -> None:
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT IGNORE INTO issue_encounter (pid, list_id, encounter, resolved)
                    VALUES (:pid, :list_id, :encounter, 0)
                """),
                {"pid": int(pid), "list_id": int(list_id), "encounter": int(encounter)},
            )
    except Exception as e:
        logger.error(
            f"past_encounter | _link_issue_to_encounter failed encounter={encounter}: {e}"
        )


def _insert_billing_rows(pid: int, encounter: int, provider_id: int) -> None:
    """
    Insert one billing row per CPT in DEMO_CPT_CODES. Each row carries the
    telehealth '95' modifier so the encounter bills as synchronous telehealth.
    Today: 99214 (E/M established patient, moderate complexity) plus 99457
    (RPM first 20 minutes) and 99458 (RPM additional 20 minutes) to match
    the diabetes-themed encounter narrative's home-glucose review.
    """
    engine = get_openemr_db_engine()
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with engine.begin() as conn:
            for code, code_text, modifier in DEMO_CPT_CODES:
                conn.execute(
                    text("""
                        INSERT INTO billing (
                            date, code_type, code, pid, provider_id, user, groupname,
                            authorized, encounter, code_text, billed, activity,
                            modifier, units, fee, justify, target, x12_partner_id
                        ) VALUES (
                            :date, 'CPT4', :code, :pid, :provider_id, :provider_id, 'Default',
                            1, :encounter, :code_text, 0, 1,
                            :modifier, 1, 0.00, '', 'IP', 0
                        )
                    """),
                    {
                        "date": today_date,
                        "code": code,
                        "pid": int(pid),
                        "provider_id": int(provider_id),
                        "encounter": int(encounter),
                        "code_text": code_text,
                        "modifier": modifier,
                    },
                )
    except Exception as e:
        logger.error(
            f"past_encounter | _insert_billing_rows failed encounter={encounter}: {e}"
        )


def _attach_care_plan_form(
    *,
    encounter: int,
    pid: int,
    provider_user_id: int,
    provider_username: str,
    body: str,
) -> None:
    """Insert form_care_plan + matching forms registry row."""
    engine = get_openemr_db_engine()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with engine.begin() as conn:
            # form_care_plan.id is NOT auto_increment (bigint, no default) —
            # unlike most form tables. OpenEMR's own care_plan/save.php assigns
            # it via MAX(id)+1 and reuses that id as the forms-registry form_id,
            # so a single form can carry multiple care-plan line rows under one
            # id. We mirror that convention; running inside engine.begin() keeps
            # the read-then-insert atomic for the serial hydrate pass. (This is
            # the form's own id sequence — unrelated to the encounter-number
            # `sequences` guardrail.)
            new_id = conn.execute(
                text("SELECT COALESCE(MAX(id), 0) + 1 FROM form_care_plan")
            ).scalar()
            conn.execute(
                text("""
                    INSERT INTO form_care_plan (
                        id, date, pid, encounter, user, groupname,
                        authorized, activity, code, codetext, description,
                        care_plan_type
                    ) VALUES (
                        :id, :date, :pid, :encounter, :user, 'Default',
                        1, 1, '', '', :description, 'plan'
                    )
                """),
                {
                    "id": int(new_id),
                    "date": now,
                    "pid": int(pid),
                    "encounter": str(encounter),
                    "user": provider_username,
                    "description": body,
                },
            )
            _register_form(
                conn, encounter, pid, provider_user_id, provider_username,
                form_name="Care Plan", formdir="care_plan",
                form_specific_id=int(new_id),
                now=now,
            )
    except Exception as e:
        logger.error(f"past_encounter | _attach_care_plan_form failed encounter={encounter}: {e}")


def _attach_clinical_instructions_form(
    *,
    encounter: int,
    pid: int,
    provider_user_id: int,
    provider_username: str,
    body: str,
) -> None:
    """Insert form_clinical_instructions + matching forms registry row."""
    engine = get_openemr_db_engine()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO form_clinical_instructions (
                        pid, encounter, user, instruction, activity
                    ) VALUES (
                        :pid, :encounter, :user, :instruction, 1
                    )
                """),
                {
                    "pid": int(pid),
                    "encounter": str(encounter),
                    "user": provider_username,
                    "instruction": body,
                },
            )
            form_specific_id = result.lastrowid
            _register_form(
                conn, encounter, pid, provider_user_id, provider_username,
                form_name="Clinical Instructions", formdir="clinical_instructions",
                form_specific_id=int(form_specific_id) if form_specific_id else 0,
                now=now,
            )
    except Exception as e:
        logger.error(f"past_encounter | _attach_clinical_instructions_form failed encounter={encounter}: {e}")


def _register_form(
    conn,
    encounter: int,
    pid: int,
    provider_user_id: int,
    provider_username: str,
    *,
    form_name: str,
    formdir: str,
    form_specific_id: int,
    now: str,
) -> None:
    """Insert a row into the forms registry table linking a form-specific row
    (form_care_plan, form_clinical_instructions, form_dictation) to the
    encounter. Shared by the _attach_*_form helpers."""
    conn.execute(
        text("""
            INSERT INTO forms (
                date, encounter, form_name, form_id, pid, user, groupname,
                authorized, deleted, formdir, provider_id
            ) VALUES (
                :date, :encounter, :form_name, :form_id, :pid, :user, 'Default',
                1, 0, :formdir, :provider_id
            )
        """),
        {
            "date": now,
            "encounter": int(encounter),
            "form_name": form_name,
            "form_id": int(form_specific_id),
            "pid": int(pid),
            "user": provider_username,
            "formdir": formdir,
            "provider_id": int(provider_user_id),
        },
    )


def _esign_all_attached_forms(encounter_number: int, signator_user_id: int) -> None:
    """
    Insert one esign_signatures row per attached, non-deleted form on the
    encounter. Each row carries table='forms' and tid=forms.id — matches
    what OpenEMR writes when a provider clicks the per-form eSign button.
    The encounter-level row (table='form_encounter') is added separately by
    _esign_encounter and is what triggers the lock cascade via lock_esign_all.
    """
    engine = get_openemr_db_engine()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with engine.begin() as conn:
            forms_rows = conn.execute(
                text("""
                    SELECT id FROM forms
                    WHERE encounter = :encounter AND deleted = 0
                """),
                {"encounter": int(encounter_number)},
            ).fetchall()
            for row in forms_rows:
                hash_value = hashlib.sha256(
                    f"zoomly:demo:form:{row.id}".encode("utf-8")
                ).hexdigest()
                conn.execute(
                    text("""
                        INSERT INTO esign_signatures (
                            tid, `table`, uid, datetime, is_lock, amendment,
                            hash, signature_hash
                        ) VALUES (
                            :tid, 'forms', :uid, :datetime, 1, NULL,
                            :hash, :sig_hash
                        )
                    """),
                    {
                        "tid": int(row.id),
                        "uid": int(signator_user_id),
                        "datetime": now,
                        "hash": hash_value,
                        "sig_hash": hash_value,
                    },
                )
    except Exception as e:
        logger.error(
            f"past_encounter | _esign_all_attached_forms failed encounter={encounter_number}: {e}"
        )


def _esign_encounter(encounter_number: int, signator_user_id: int) -> None:
    """
    Insert single esign_signatures row on the encounter. With lock_esign_all=1
    in OpenEMR globals, this locks both the encounter and all attached forms.
    """
    engine = get_openemr_db_engine()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # Deterministic hash so re-runs (if they ever happened) would be stable.
    # Demo content is fixed at seed time, so a non-cryptographic placeholder
    # is fine — this satisfies the NOT NULL constraint.
    hash_value = hashlib.sha256(
        f"zoomly:demo:encounter:{encounter_number}".encode("utf-8")
    ).hexdigest()
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO esign_signatures (
                        tid, `table`, uid, datetime, is_lock, amendment,
                        hash, signature_hash
                    ) VALUES (
                        :tid, 'form_encounter', :uid, :datetime, 1, NULL,
                        :hash, :sig_hash
                    )
                """),
                {
                    "tid": int(encounter_number),
                    "uid": int(signator_user_id),
                    "datetime": now,
                    "hash": hash_value,
                    "sig_hash": hash_value,
                },
            )
    except Exception as e:
        logger.error(
            f"past_encounter | _esign_encounter failed encounter={encounter_number}: {e}"
        )


# ---------------------------------------------------------------------------
# Summary bookkeeping
# ---------------------------------------------------------------------------

def _record_skip(summary: dict, account: ZoomAccount, provider_user_id: int, reason: str) -> None:
    write_audit_log(
        event_type="demo.past_encounter_skipped",
        success=True,
        zoom_account_id=account.account_id,
        openemr_user_id=str(provider_user_id),
        detail={"reason": reason},
    )
    summary["past_encounter_skips"].append({
        "openemr_user_id": str(provider_user_id),
        "reason": reason,
    })


def _record_error(summary: dict, account: ZoomAccount, provider_user_id: int, stage: str, message: str) -> None:
    write_audit_log(
        event_type="demo.past_encounter_failed",
        success=False,
        zoom_account_id=account.account_id,
        openemr_user_id=str(provider_user_id),
        error_message=message,
        detail={"stage": stage},
    )
    summary["past_encounter_errors"].append({
        "openemr_user_id": str(provider_user_id),
        "stage": stage,
        "error": message,
    })
