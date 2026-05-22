"""
Sprint 13 demo hydration orchestrator.

Walks every active ProviderMapping for a registered ZoomAccount and ensures
the next-2-weekdays x 2-slots-per-day grid (= 4 slots per provider) is fully
populated with appointments + Zoom meetings. Idempotent — re-running tops up
any slot missing an appointment, or backfills a Zoom meeting on an existing
appointment that lacks a MeetingRecord.

Respects each account's AppointmentTypeFilter — if the SE has narrowed
allowed appointment types, hydration only considers categories that are
both (a) compatible with the provider's specialty and (b) in the account's
filter list. Mirrors filter_appointment_event so hydration never creates
state the production filter would have dropped.

Lives at the top level of services/ (alongside meeting.py and audit.py)
because the orchestrator coordinates across both OpenEMR and Zoom domains
and isn't owned by either. See follow-up backlog item — broader
services/ layout review planned.
"""

import logging
from datetime import date, time, timedelta

from sqlalchemy import text

from app.extensions import get_openemr_db_engine
from app.models import (
    AppointmentTypeFilter,
    MeetingRecord,
    ProviderMapping,
    ZoomAccount,
)
from app.services.audit import write_audit_log
from app.services.meeting import create_meeting_for_appointment
from app.services.openemr import (
    generate_future_appointment,
    get_provider_appointments_in_window,
    get_provider_patients,
    get_provider_specialty_categories,
)
from app.services.openemr.appointments.appointment_processor import AppointmentMatch


logger = logging.getLogger(__name__)


# Two slots per weekday — first morning, mid-afternoon.
_SLOT_TIMES = [time(9, 0), time(14, 0)]


def hydrate_future_meetings(account: ZoomAccount) -> dict:
    """
    For each active mapped provider on the account, ensure the next 4 weekday
    slots (tomorrow 9am/2pm + day-after 9am/2pm) carry both an appointment
    and a real Zoom meeting.

    Returns a summary dict suitable for surfacing in the React response:

        {
            "providers_processed": int,
            "providers_skipped": [{"openemr_provider_id": "10", "reason": "no_patients"}, ...],
            "appointments_created": int,
            "meetings_created": int,
            "meetings_backfilled": int,
            "errors": [...],
        }
    """
    write_audit_log(
        event_type="demo.hydrate_started",
        success=True,
        zoom_account_id=account.account_id,
    )

    summary = {
        "providers_processed": 0,
        "providers_skipped": [],
        "appointments_created": 0,
        "meetings_created": 0,
        "meetings_backfilled": 0,
        "errors": [],
    }

    slot_dates = _next_two_weekdays(date.today())
    slot_grid = [(d, t) for d in slot_dates for t in _SLOT_TIMES]

    category_id_map = _load_category_id_map()

    filter_rows = AppointmentTypeFilter.query.filter_by(
        zoom_account_id=account.account_id
    ).all()
    # None = no filter configured (open — pass all categories). Set otherwise.
    filter_type_ids = (
        {int(f.openemr_type_id) for f in filter_rows} if filter_rows else None
    )

    mappings = ProviderMapping.query.filter_by(
        zoom_account_id=account.account_id, is_active=True
    ).all()

    for mapping in mappings:
        provider_user_id = int(mapping.openemr_provider_id)

        skip_reason, effective_categories, patients = _evaluate_provider(
            provider_user_id, category_id_map, filter_type_ids
        )
        if skip_reason:
            write_audit_log(
                event_type="demo.hydrate_provider_skipped",
                success=True,
                zoom_account_id=account.account_id,
                openemr_provider_id=str(provider_user_id),
                detail={"reason": skip_reason},
            )
            summary["providers_skipped"].append({
                "openemr_provider_id": str(provider_user_id),
                "reason": skip_reason,
            })
            continue

        existing_appts = get_provider_appointments_in_window(
            provider_user_id, slot_dates[0], slot_dates[-1]
        )

        for i, (slot_date, slot_time) in enumerate(slot_grid):
            patient = patients[i % len(patients)]
            category_name, category_id = effective_categories[i % len(effective_categories)]

            existing = _find_existing_appt_for_slot(existing_appts, slot_date, slot_time)
            if existing is None:
                _handle_empty_slot(
                    account=account, mapping=mapping, provider_user_id=provider_user_id,
                    patient=patient, category_name=category_name, category_id=category_id,
                    slot_date=slot_date, slot_time=slot_time, summary=summary,
                )
            else:
                _handle_existing_slot(
                    account=account, mapping=mapping, provider_user_id=provider_user_id,
                    existing=existing, slot_date=slot_date, slot_time=slot_time,
                    summary=summary,
                )

        summary["providers_processed"] += 1

    write_audit_log(
        event_type="demo.hydrate_completed",
        success=True,
        zoom_account_id=account.account_id,
        detail=summary,
    )
    return summary


# ---------------------------------------------------------------------------
# Per-provider gating
# ---------------------------------------------------------------------------

def _evaluate_provider(
    provider_user_id: int,
    category_id_map: dict[str, int],
    filter_type_ids: set[int] | None,
) -> tuple[str | None, list[tuple[str, int]], list[dict]]:
    """
    Decide whether the provider can be hydrated.

    Returns:
        (skip_reason, effective_categories, patients)
        skip_reason is None on success; otherwise one of:
          "unknown_specialty" | "no_matching_categories" | "no_patients"
    """
    specialty_names = get_provider_specialty_categories(provider_user_id)
    if not specialty_names:
        return "unknown_specialty", [], []

    effective_categories: list[tuple[str, int]] = []
    for name in specialty_names:
        cat_id = category_id_map.get(name)
        if cat_id is None:
            logger.warning(
                f"hydrate | provider={provider_user_id} specialty category "
                f"'{name}' not present in openemr_postcalendar_categories — skipping"
            )
            continue
        if filter_type_ids is not None and cat_id not in filter_type_ids:
            continue
        effective_categories.append((name, cat_id))
    if not effective_categories:
        return "no_matching_categories", [], []

    patients = get_provider_patients(provider_user_id)
    if not patients:
        return "no_patients", [], []

    return None, effective_categories, patients


# ---------------------------------------------------------------------------
# Per-slot actions
# ---------------------------------------------------------------------------

def _handle_empty_slot(
    *, account, mapping, provider_user_id, patient,
    category_name, category_id, slot_date, slot_time, summary,
) -> None:
    """Create appointment + Zoom meeting for an empty slot."""
    facility_id = (
        int(mapping.openemr_facility_id)
        if mapping.openemr_facility_id
        else _lookup_provider_facility(provider_user_id)
    )

    new_eid = generate_future_appointment(
        zoom_account_id=account.account_id,
        provider_user_id=provider_user_id,
        facility_id=facility_id,
        patient_pid=int(patient["pid"]),
        category_id=category_id,
        category_name=category_name,
        slot_date=slot_date,
        slot_time=slot_time,
    )
    if new_eid is None:
        summary["errors"].append({
            "stage": "generate_appointment",
            "openemr_provider_id": str(provider_user_id),
            "slot": f"{slot_date.isoformat()}T{slot_time.isoformat()}",
        })
        return
    summary["appointments_created"] += 1

    # Synthetic payload mirroring the OpenEMR webhook shape so create_zoom_meeting
    # has all the fields it expects (appointment_date YYYY-MM-DD, appointment_time HH:MM,
    # title, duration_minutes).
    payload = {
        "eid": new_eid,
        "pid": patient["pid"],
        "appt_status": "-",
        "appointment_date": slot_date.strftime("%Y-%m-%d"),
        "appointment_time": slot_time.strftime("%H:%M"),
        "title": category_name,
        "duration_minutes": 30,
    }
    match = AppointmentMatch(zoom_account=account, provider_mapping=mapping, payload=payload)
    result = create_meeting_for_appointment(match, payload)
    if "error" in result:
        summary["errors"].append({
            "stage": "create_meeting",
            "openemr_provider_id": str(provider_user_id),
            "openemr_appointment_id": new_eid,
            "error": result["error"],
        })
        return
    summary["meetings_created"] += 1
    write_audit_log(
        event_type="demo.future_meeting_created",
        success=True,
        zoom_account_id=account.account_id,
        openemr_provider_id=str(provider_user_id),
        openemr_patient_id=str(patient["pid"]),
        openemr_appointment_id=str(new_eid),
        zoom_meeting_id=result.get("zoom_meeting_id"),
        detail={
            "slot_date": slot_date.isoformat(),
            "slot_time": slot_time.isoformat(),
            "category_name": category_name,
        },
    )


def _handle_existing_slot(
    *, account, mapping, provider_user_id, existing,
    slot_date, slot_time, summary,
) -> None:
    """If the existing appointment lacks a MeetingRecord, backfill it. Else no-op."""
    existing_eid = existing["pc_eid"]
    existing_pid = existing["pc_pid"]
    appt_status = existing.get("pc_apptstatus") or "-"

    meeting_record = MeetingRecord.query.filter_by(
        openemr_appointment_id=str(existing_eid),
        zoom_account_id=account.account_id,
    ).first()
    if meeting_record:
        # Both present — silent no-op (audit volume kept sane per design).
        return

    # Synthetic payload mirroring the OpenEMR webhook shape — backfill path
    # reuses the existing appointment's date/time/title/duration.
    existing_duration_sec = existing.get("pc_duration") or 1800
    payload = {
        "eid": existing_eid,
        "pid": existing_pid,
        "appt_status": appt_status,
        "appointment_date": slot_date.strftime("%Y-%m-%d"),
        "appointment_time": slot_time.strftime("%H:%M"),
        "title": existing.get("pc_title") or "Telehealth Visit",
        "duration_minutes": max(1, int(existing_duration_sec) // 60),
        "comments": existing.get("pc_hometext") or "",
    }
    match = AppointmentMatch(zoom_account=account, provider_mapping=mapping, payload=payload)
    result = create_meeting_for_appointment(match, payload)
    if "error" in result:
        summary["errors"].append({
            "stage": "backfill_meeting",
            "openemr_provider_id": str(provider_user_id),
            "openemr_appointment_id": existing_eid,
            "error": result["error"],
        })
        return
    summary["meetings_backfilled"] += 1
    write_audit_log(
        event_type="demo.future_meeting_backfilled",
        success=True,
        zoom_account_id=account.account_id,
        openemr_provider_id=str(provider_user_id),
        openemr_patient_id=str(existing_pid),
        openemr_appointment_id=str(existing_eid),
        zoom_meeting_id=result.get("zoom_meeting_id"),
        detail={
            "slot_date": slot_date.isoformat(),
            "slot_time": slot_time.isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Slot grid + lookups
# ---------------------------------------------------------------------------

def _next_two_weekdays(start: date) -> list[date]:
    """Return the next 2 weekday dates strictly after `start` (skips Sat/Sun)."""
    result: list[date] = []
    candidate = start
    while len(result) < 2:
        candidate = candidate + timedelta(days=1)
        if candidate.weekday() < 5:  # 0=Mon..4=Fri
            result.append(candidate)
    return result


def _load_category_id_map() -> dict[str, int]:
    """name → pc_catid lookup for active appointment categories."""
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT pc_catid, pc_catname FROM openemr_postcalendar_categories WHERE pc_active = 1"
        )).fetchall()
    return {row.pc_catname: int(row.pc_catid) for row in rows}


def _find_existing_appt_for_slot(
    appts: list[dict], slot_date: date, slot_time: time
) -> dict | None:
    for appt in appts:
        if appt["pc_eventDate"] == slot_date and appt["pc_startTime"] == slot_time:
            return appt
    return None


def _lookup_provider_facility(provider_user_id: int) -> int:
    """
    Fallback for pre-S7-14 ProviderMappings whose openemr_facility_id is NULL.
    Returns the provider's users.facility_id (0 if unresolvable).
    """
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT facility_id FROM users WHERE id = :id"),
            {"id": int(provider_user_id)}
        ).fetchone()
    return int(row.facility_id) if row and row.facility_id else 0
