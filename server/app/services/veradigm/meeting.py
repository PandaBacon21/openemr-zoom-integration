"""
Veradigm external appointment page — Start/Join meeting mint-or-reuse.

Reuses create_zoom_meeting() (the pure "make me a Zoom meeting" call) and
persists to the isolated VeradigmMeeting table. Deliberately does NOT call
create_meeting_for_appointment() — that writes pc_website back to OpenEMR and
creates a MeetingRecord, which would pull the appointment into the Epic
note-writeback / status pipeline.
"""

import logging
from datetime import time, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db, get_openemr_db_engine
from app.models import UserMapping, VeradigmMeeting
from app.services.audit import write_audit_log
from app.services.zoom import create_zoom_meeting
from app.services.openemr.appointments.appointment_processor import AppointmentMatch
from app.services.veradigm.appointments import veradigm_category_ids

logger = logging.getLogger(__name__)


def _to_hhmm(value) -> str | None:
    """Normalize a MariaDB TIME (timedelta via PyMySQL, or datetime.time) to HH:MM."""
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    return None


def _fetch_appointment(eid: int) -> dict | None:
    """Single-appointment read with the fields create_zoom_meeting's payload needs."""
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT pc_pid, pc_aid, pc_catid, pc_eventDate, pc_startTime,
                       pc_duration, pc_title
                FROM openemr_postcalendar_events
                WHERE pc_eid = :eid
            """),
            {"eid": int(eid)},
        ).fetchone()
    if not row:
        return None
    return {
        "pid": row.pc_pid,
        "aid": row.pc_aid,
        "catid": row.pc_catid,
        "event_date": row.pc_eventDate,
        "start_time": row.pc_startTime,
        "duration": row.pc_duration,
        "title": row.pc_title,
    }


def _meeting_dict(m: VeradigmMeeting, reused: bool) -> dict:
    return {
        "meeting_id": m.zoom_meeting_id,
        "start_url": m.start_url,
        "join_url": m.join_url,
        "reused": reused,
    }


def get_or_create_veradigm_meeting(account, eid: str) -> dict:
    """
    Return the Zoom meeting for a Veradigm appointment, minting it on first use.

    Returns {"meeting_id", "start_url", "join_url", "reused"} on success, or
    {"error": "<reason>"} on failure.
    """
    eid = str(eid)

    existing = db.session.get(VeradigmMeeting, eid)
    if existing:
        return _meeting_dict(existing, reused=True)

    appt = _fetch_appointment(eid)
    if not appt:
        return {"error": "appointment_not_found"}

    # Defense-in-depth: only mint for appointments the account designates Veradigm.
    if str(appt["catid"]) not in veradigm_category_ids(account.account_id):
        return {"error": "not_veradigm_appointment"}

    mapping = UserMapping.query.filter_by(
        zoom_account_id=account.account_id,
        openemr_user_id=str(appt["aid"]),
        is_provider=True,
        is_active=True,
    ).first()
    if not mapping:
        return {"error": "provider_not_mapped"}

    event_date = appt["event_date"]
    payload = {
        "eid": eid,
        "pid": appt["pid"],
        "appointment_date": event_date.strftime("%Y-%m-%d") if event_date else None,
        "appointment_time": _to_hhmm(appt["start_time"]),
        "title": appt["title"] or "Veradigm Telehealth Visit",
        "duration_minutes": int(appt["duration"]) // 60 if appt.get("duration") else 30,
    }
    match = AppointmentMatch(zoom_account=account, provider_mapping=mapping, payload=payload)

    try:
        meeting_data = create_zoom_meeting(match)
    except Exception as e:
        logger.error(f"veradigm.meeting | eid={eid} Zoom create failed: {e}")
        write_audit_log(
            event_type="veradigm.meeting_create_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_user_id=str(appt["aid"]),
            openemr_patient_id=str(appt["pid"]) if appt.get("pid") is not None else None,
            error_message=str(e),
        )
        return {"error": "zoom_create_failed"}

    record = VeradigmMeeting(
        openemr_appointment_id=eid,
        zoom_account_id=account.account_id,
        openemr_provider_user_id=str(appt["aid"]),
        zoom_meeting_id=meeting_data["meeting_id"],
        start_url=meeting_data["start_url"],
        join_url=meeting_data["join_url"],
    )
    db.session.add(record)
    try:
        db.session.commit()
    except IntegrityError:
        # Concurrent mint for the same appointment — reuse the row that won.
        db.session.rollback()
        winner = db.session.get(VeradigmMeeting, eid)
        if winner:
            return _meeting_dict(winner, reused=True)
        raise

    write_audit_log(
        event_type="veradigm.meeting_created",
        success=True,
        zoom_account_id=account.account_id,
        openemr_appointment_id=eid,
        openemr_user_id=str(appt["aid"]),
        openemr_patient_id=str(appt["pid"]) if appt.get("pid") is not None else None,
        zoom_meeting_id=meeting_data["meeting_id"],
    )
    return _meeting_dict(record, reused=False)
