import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from app.extensions import get_openemr_db_engine


logger = logging.getLogger(__name__)


def find_encounter_for_appointment(eid: int, pid: int, provider_id: int) -> tuple[int | None, str | None]:
    """
    Find an existing encounter for a given appointment.

    Lookup order (patient_tracker.encounter is now the canonical pointer —
    OpenEMR's PHP path keeps it in sync on every status change that auto-
    creates an encounter, and every Zoomly direct-write path calls
    upsert_patient_tracker too):

        1. patient_tracker.encounter for this eid (non-zero)        → 'tracker'
        2. form_encounter.external_id = 'zoom_eid_{eid}'            → 'external_id'
           Legacy fallback for the gap window before tracker
           backfills land on all existing appointments.
        3. Most recent encounter for pid + provider_id on today's   → 'manual_fallback'
           date with no external_id. Stamps external_id on the way
           out so subsequent lookups hit a faster path.

    Returns:
        (encounter_number, source)
          encounter_number: int or None if no encounter found
          source:           "tracker" | "external_id" | "manual_fallback" | None
    """
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            # --- 1. Canonical: patient_tracker.encounter ---
            result = conn.execute(
                text("SELECT encounter FROM patient_tracker WHERE eid = :eid AND encounter > 0 LIMIT 1"),
                {"eid": int(eid)}
            ).fetchone()
            if result:
                logger.info(
                    f"openemr.find_encounter | Found via patient_tracker eid={eid} "
                    f"→ encounter={result.encounter}"
                )
                return result.encounter, "tracker"

            # --- 2. Legacy fallback: external_id = 'zoom_eid_{eid}' ---
            result = conn.execute(
                text("""
                    SELECT encounter FROM form_encounter
                    WHERE external_id = :external_id
                    LIMIT 1
                """),
                {"external_id": f"zoom_eid_{eid}"}
            ).fetchone()

            if result:
                logger.info(
                    f"openemr.find_encounter | Found by external_id zoom_eid_{eid} "
                    f"→ encounter={result.encounter}"
                )
                return result.encounter, "external_id"

            # --- 3. Manual fallback: UI-created encounter on today's date ---
            result = conn.execute(
                text("""
                    SELECT encounter FROM form_encounter
                    WHERE pid = :pid
                    AND provider_id = :provider_id
                    AND DATE(date) = CURDATE()
                    AND (external_id IS NULL OR external_id = '')
                    ORDER BY encounter DESC
                    LIMIT 1
                """),
                {"pid": int(pid), "provider_id": int(provider_id)}
            ).fetchone()

            if result:
                conn.execute(
                    text("""
                        UPDATE form_encounter
                        SET external_id = :external_id
                        WHERE encounter = :encounter
                    """),
                    {"external_id": f"zoom_eid_{eid}", "encounter": result.encounter}
                )
                logger.info(
                    f"openemr.find_encounter | Found manually-created encounter "
                    f"pid={pid} provider={provider_id} → encounter={result.encounter} "
                    f"— stamped external_id=zoom_eid_{eid}"
                )
                return result.encounter, "manual_fallback"

    except Exception as e:
        logger.error(f"openemr.find_encounter | Failed for eid={eid}: {e}")

    return None, None


def ensure_encounter_for_appointment(
    *,
    eid: int,
    pid: int,
    provider_id: int,
    facility_id: int,
    pc_catid: int,
    reason: str = "Zoom Telehealth Visit",
    class_code: str = "VR",
) -> tuple[int | None, str | None]:
    """
    Idempotent find-or-create for the encounter tied to an appointment.

    The canonical single-encounter-per-appointment helper — any code path
    that needs the encounter for an appointment (provider start via Zoom
    button or meeting.started webhook, patient arrival via waiting-room
    webhook, clinical-note writeback safety net) should call this rather
    than `find_encounter_for_appointment` + `create_encounter` directly.

    Lookup priority comes from `find_encounter_for_appointment`:
      1. patient_tracker.encounter for this eid → source='tracker'
      2. form_encounter.external_id='zoom_eid_{eid}' → source='external_id'
      3. manually-created encounter on today's date with no external_id
         → source='manual_fallback' (stamps external_id on the way out)

    If none of the above resolves, a new encounter is created via
    `create_encounter`, which in turn populates patient_tracker.encounter
    so subsequent ensure_* calls hit the tracker path. Source on creation
    is 'created'.

    Returns:
        (encounter_number, source)
          source: "tracker" | "external_id" | "manual_fallback" | "created" | None
        Returns (None, None) only on a hard failure inside create_encounter.
    """
    encounter, source = find_encounter_for_appointment(
        eid=int(eid), pid=int(pid), provider_id=int(provider_id)
    )
    if encounter is not None:
        return encounter, source

    new_encounter = create_encounter(
        pid=int(pid),
        provider_id=int(provider_id),
        facility_id=int(facility_id),
        pc_catid=int(pc_catid),
        eid=int(eid),
        reason=reason,
        class_code=class_code,
    )
    if new_encounter is None:
        return None, None
    return new_encounter, "created"


def create_encounter(
    pid: int,
    provider_id: int,
    facility_id: int,
    pc_catid: int,
    eid: int,
    reason: str = "Zoom Telehealth Visit",
    class_code: str = "VR",
) -> int | None:
    """
    Create a new encounter in OpenEMR linked to a Zoom appointment.

    Replicates what OpenEMR's auto-create encounter does when appointment
    status is changed to Arrived via the UI.
    - changing via the direct DB connection does not trigger the auto-create function
    

    Uses the sequences table to get the next encounter number atomically.
    Sets external_id = 'zoom_eid_{eid}' for reliable lookup later.

    Args:
        pid:         OpenEMR patient ID
        provider_id: OpenEMR provider users.id
        facility_id: OpenEMR facility ID
        pc_catid:    Calendar category ID (appointment type)
        eid:         OpenEMR appointment EID (stored in external_id)
        reason:      Reason for visit text
        class_code:  HL7 encounter class — 'VR' for virtual

    Returns:
        encounter number (int) if successful, None on failure
    """

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            # Check if encounter already exists for this eid
            existing = conn.execute(
                text("SELECT encounter FROM form_encounter WHERE external_id = :external_id"),
                {"external_id": f"zoom_eid_{eid}"}
            ).fetchone()

            if existing:
                logger.info(f"openemr.create_encounter | Encounter already exists for eid={eid}, skipping")
                return existing.encounter
            
            # --- 1. If not existing - Get next encounter number atomically ---
            conn.execute(text("UPDATE sequences SET id = id + 1"))
            result = conn.execute(text("SELECT id FROM sequences"))
            encounter_number = result.scalar()

            # --- 2. Insert form_encounter ---
            encounter_uuid = uuid.uuid4().bytes
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")

            conn.execute(
                text("""
                    INSERT INTO form_encounter (
                        uuid, date, pid, encounter,
                        pc_catid, provider_id, facility_id,
                        billing_facility, class_code,
                        reason, external_id,
                        sensitivity, in_collection
                    ) VALUES (
                        :uuid, :date, :pid, :encounter,
                        :pc_catid, :provider_id, :facility_id,
                        :billing_facility, :class_code,
                        :reason, :external_id,
                        '', 0
                    )
                """),
                {
                    "uuid": encounter_uuid,
                    "date": today,
                    "pid": int(pid),
                    "encounter": encounter_number,
                    "pc_catid": int(pc_catid),
                    "provider_id": int(provider_id),
                    "facility_id": int(facility_id),
                    "billing_facility": int(facility_id),
                    "class_code": class_code,
                    "reason": reason,
                    "external_id": f"zoom_eid_{eid}",
                }
            )
            # Look up provider username for forms.user field
            user_result = conn.execute(
                text("SELECT username FROM users WHERE id = :provider_id"),
                {"provider_id": int(provider_id)}
            )
            row = user_result.fetchone()
            provider_username = row.username if row else "admin"

            # --- 3. Insert forms table entry to link encounter form ---
            forms_result = conn.execute(
                text("""
                    INSERT INTO forms (
                        date, encounter, form_name, formdir,
                        pid, authorized, deleted, provider_id, user, groupname
                    ) VALUES (
                        :date, :encounter, :form_name, :formdir,
                        :pid, 1, 0, :provider_id, :user, 'Default'
                    )
                """),
                {
                    "date": now,
                    "encounter": encounter_number,
                    "form_name": "New Patient Encounter",
                    "formdir": "newpatient",
                    "pid": int(pid),
                    "provider_id": int(provider_id),
                    "user": provider_username
                }
            )
            # --- 4. Set form_id to self-referential id ---
            forms_id = forms_result.lastrowid
            conn.execute(
                text("UPDATE forms SET form_id = :form_id WHERE id = :id"),
                {"form_id": forms_id, "id": forms_id}
            )

        logger.info(
            f"openemr.create_encounter | Created encounter={encounter_number} "
            f"pid={pid} eid={eid} provider={provider_id}"
        )
        _link_encounter_to_tracker(eid=int(eid), pid=int(pid), encounter=int(encounter_number))
        return encounter_number

    except Exception as e:
        logger.error(f"openemr.create_encounter | Failed for pid={pid} eid={eid}: {e}")
        return None


def _link_encounter_to_tracker(*, eid: int, pid: int, encounter: int) -> None:
    """
    Update patient_tracker.encounter for the appointment (or insert a tracker
    row if none exists). Pulls apptdate/appttime from openemr_postcalendar_events
    since this helper is called from contexts that don't have them on hand.

    Kept separate from create_encounter's transaction so a tracker write
    failure doesn't roll back the encounter insert — the encounter is the
    primary artifact and is recoverable via the legacy external_id lookup
    paths if the tracker write fails.
    """
    # Local import to avoid a top-level cycle with services.openemr.appointments
    # (appointment.py → upsert_patient_tracker; encounter.py is imported from
    # services.openemr.__init__ before appointments are pulled in).
    from app.services.openemr.appointments.appointment import upsert_patient_tracker

    engine = get_openemr_db_engine()
    try:
        with engine.connect() as conn:
            appt = conn.execute(
                text("""
                    SELECT pc_eventDate, pc_startTime
                    FROM openemr_postcalendar_events
                    WHERE pc_eid = :eid
                    LIMIT 1
                """),
                {"eid": int(eid)},
            ).fetchone()
    except Exception as e:
        logger.error(
            f"openemr._link_encounter_to_tracker | appt lookup failed eid={eid}: {e}"
        )
        return

    if not appt:
        logger.warning(
            f"openemr._link_encounter_to_tracker | no appointment row for eid={eid} — tracker not updated"
        )
        return

    # pc_startTime arrives as a timedelta from PyMySQL; convert to time.
    from datetime import time as _time
    start_td = appt.pc_startTime
    if start_td is None:
        appttime = _time(0, 0)
    elif hasattr(start_td, "total_seconds"):
        total = int(start_td.total_seconds())
        appttime = _time(total // 3600, (total % 3600) // 60, total % 60)
    else:
        appttime = start_td

    upsert_patient_tracker(
        eid=int(eid),
        pid=int(pid),
        apptdate=appt.pc_eventDate,
        appttime=appttime,
        encounter=int(encounter),
        original_user="zoomly_webhook_encounter",
    )

