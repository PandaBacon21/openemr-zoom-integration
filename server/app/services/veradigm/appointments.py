"""
Veradigm external appointment page — appointment list assembly.

Reads the same windowed appointment source the hydration flow uses
(get_provider_appointments_in_window), filters to the account's Veradigm
appointment types, and enriches each row with patient/provider names and any
already-minted Veradigm meeting URLs. Read-only; no OpenEMR writeback.
"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import bindparam, text

from app.extensions import get_openemr_db_engine
from app.models import AppointmentTypeFilter, UserMapping, VeradigmMeeting
from app.services.openemr import get_provider_appointments_in_window

logger = logging.getLogger(__name__)


def appointment_window(today: date | None = None) -> tuple[date, date]:
    """Return the inclusive window from LAST week's Monday to NEXT week's Sunday
    (three calendar weeks).

    The external page loads the whole window at once; the Today / Future
    (this|next week) / Past views are filtered client-side from this set. Last
    week is included so the Past view can show recently-completed visits.
    """
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(days=7), monday + timedelta(days=13)


def veradigm_category_ids(zoom_account_id: str) -> set[str]:
    """The account's Veradigm-designated appointment category ids (as strings)."""
    rows = AppointmentTypeFilter.query.filter_by(
        zoom_account_id=zoom_account_id, integration="veradigm"
    ).all()
    return {str(r.openemr_type_id) for r in rows}


def provider_mappings_for_account(zoom_account_id: str) -> list[UserMapping]:
    """All active provider-role mappings for the account."""
    return (
        UserMapping.query
        .filter_by(zoom_account_id=zoom_account_id, is_provider=True, is_active=True)
        .all()
    )


def _resolve_patient_names(pids: set[str]) -> dict[str, str]:
    """Bulk map pid -> 'First Last' from OpenEMR patient_data."""
    if not pids:
        return {}
    engine = get_openemr_db_engine()
    int_pids = [int(p) for p in pids if str(p).isdigit()]
    if not int_pids:
        return {}
    stmt = text(
        "SELECT pid, fname, lname FROM patient_data WHERE pid IN :pids"
    ).bindparams(bindparam("pids", expanding=True))
    with engine.connect() as conn:
        rows = conn.execute(stmt, {"pids": int_pids}).fetchall()
    return {
        str(r.pid): " ".join(part for part in (r.fname, r.lname) if part).strip()
        for r in rows
    }


def _existing_meetings(eids: set[str]) -> dict[str, VeradigmMeeting]:
    """Map appointment id -> VeradigmMeeting for any already-minted meetings."""
    if not eids:
        return {}
    rows = VeradigmMeeting.query.filter(
        VeradigmMeeting.openemr_appointment_id.in_(list(eids))
    ).all()
    return {m.openemr_appointment_id: m for m in rows}


def build_appointments_response(
    zoom_account_id: str,
    mappings: list[UserMapping],
    default_provider_id: str | None = None,
    today: date | None = None,
) -> dict:
    """
    Assemble the external Veradigm appointment page payload: every Veradigm-typed
    appointment across last / this / next week for the given provider mappings.
    The Today / Future (this|next week) / Past views and their counts are derived
    client-side from this single set, optionally narrowed to one provider.

    `providers` is the full Veradigm-provider directory (from the mappings, even
    those without appointments) so the page's search can list them. In EHR
    context `default_provider_id` is the launching provider (the page defaults to
    them); in admin context it's None (defaults to all).

    Returns:
        {
          "today": "YYYY-MM-DD",
          "default_provider_id": "<id>" | null,
          "providers": [ {"id": .., "name": ..}, ... ],
          "appointments": [ {appointment_id, patient_id, patient_name,
                             provider_id, provider_name, appointment_type,
                             start_time, end_time, status, has_meeting,
                             start_url, join_url}, ... ]
        }
    """
    today = today or date.today()
    start_date, end_date = appointment_window(today)
    cat_ids = veradigm_category_ids(zoom_account_id)

    providers = [
        {"id": str(m.openemr_user_id), "name": m.openemr_provider_name or str(m.openemr_user_id)}
        for m in mappings
        if m.openemr_user_id
    ]
    base = {
        "today": today.isoformat(),
        "default_provider_id": str(default_provider_id) if default_provider_id else None,
        "providers": providers,
    }

    if not cat_ids or not mappings:
        return {**base, "appointments": []}

    rows: list[dict] = []
    provider_names: dict[str, str] = {}
    for mapping in mappings:
        provider_id = mapping.openemr_user_id
        if not provider_id:
            continue
        provider_names[str(provider_id)] = (
            mapping.openemr_provider_name or str(provider_id)
        )
        for row in get_provider_appointments_in_window(
            int(provider_id), start_date, end_date
        ):
            if str(row["pc_catid"]) not in cat_ids:
                continue
            row["_provider_id"] = str(provider_id)
            rows.append(row)

    pids = {str(r["pc_pid"]) for r in rows if r.get("pc_pid") is not None}
    eids = {str(r["pc_eid"]) for r in rows}
    patient_names = _resolve_patient_names(pids)
    meetings = _existing_meetings(eids)

    appointments = []
    for r in rows:
        eid = str(r["pc_eid"])
        ev_date: date = r["pc_eventDate"]
        ev_time = r["pc_startTime"]
        start_dt = _combine(ev_date, ev_time)
        end_dt = (
            start_dt + timedelta(seconds=int(r["pc_duration"]))
            if start_dt and r.get("pc_duration")
            else None
        )
        meeting = meetings.get(eid)
        appointments.append({
            "appointment_id": eid,
            "patient_id": str(r["pc_pid"]) if r.get("pc_pid") is not None else None,
            "patient_name": patient_names.get(str(r["pc_pid"]), ""),
            "provider_id": r["_provider_id"],
            "provider_name": provider_names.get(r["_provider_id"], r["_provider_id"]),
            "appointment_type": r.get("pc_title") or "",
            "start_time": start_dt.isoformat() if start_dt else None,
            "end_time": end_dt.isoformat() if end_dt else None,
            "status": r.get("pc_apptstatus"),
            "has_meeting": meeting is not None,
            "start_url": meeting.start_url if meeting else None,
            "join_url": meeting.join_url if meeting else None,
        })

    appointments.sort(key=lambda a: a["start_time"] or "")

    return {**base, "appointments": appointments}


def _combine(ev_date, ev_time) -> datetime | None:
    """Combine a date + time (time may be None) into a datetime."""
    if ev_date is None:
        return None
    if ev_time is None:
        return datetime(ev_date.year, ev_date.month, ev_date.day)
    return datetime.combine(ev_date, ev_time)
