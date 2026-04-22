import json
import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models import AuditLog

logger = logging.getLogger(__name__)


def write_audit_log(
    event_type: str,
    success: bool,
    zoom_account_id: str | None = None,
    openemr_appointment_id: str | None = None,
    openemr_provider_id: str | None = None,
    openemr_patient_id: str | None = None,
    zoom_meeting_id: str | None = None,
    zoom_note_id: str | None = None,
    error_message: str | None = None,
    detail: dict | None = None,
) -> None:
    """
    Write an entry to the audit log.

    Never raises — audit logging must never cause a request to fail.
    If the write fails, the error is logged to the app logger and silently swallowed.

    Event types for appointment/meeting pipeline:
      appointment.received          — inbound webhook accepted and validated
      appointment.dropped           — filtered out (no matching provider/type)
      meeting.created               — Zoom meeting created successfully
      meeting.updated               — Zoom meeting patched with new appointment details
      meeting.recreated             — replacement meeting created after Zoom deletion
      meeting.deleted               — Zoom meeting deleted on appointment delete
      meeting.create_failed         — Zoom API error during meeting creation
      meeting.update_failed         — Zoom API error during meeting update
      meeting.delete_failed         — Zoom API error during meeting delete
      openemr.url_writeback_success - Zoom Meeting links written to OpenEMR Appointment Record
      openemr.url_writeback_failed  - Zoom Meeting links failed when writing to OpenEMR Appointment Record

    Event types for clinical note pipeline:
      note.received             — clinical note webhook received from Zoom
      note.retrieved            — note content fetched from Zoom API
      note.written              — note written back to OpenEMR successfully
      note.write_failed         — error writing note to OpenEMR
      zoom.completion_success   — Zoom meeting marked complete successfully
      zoom.completion_error     — error marking Zoom meeting complete

    Args:
        event_type:               One of the event type strings above
        success:                  Whether the operation succeeded
        zoom_account_id:          Zoom account ID string (not internal PK)
        openemr_appointment_id:   OpenEMR appointment eid
        openemr_provider_id:      OpenEMR provider users.id
        openemr_patient_id:       OpenEMR patient pid
        zoom_meeting_id:          Zoom meeting ID string
        zoom_note_id:             Zoom clinical note ID string
        error_message:            Error message if success=False
        detail:                   Optional dict of extra context — stored as JSON
    """
    try:
        entry = AuditLog(
            event_type=event_type,
            success=success,
            zoom_account_id=zoom_account_id,
            openemr_appointment_id=str(openemr_appointment_id) if openemr_appointment_id is not None else None,
            openemr_provider_id=str(openemr_provider_id) if openemr_provider_id is not None else None,
            openemr_patient_id=str(openemr_patient_id) if openemr_patient_id is not None else None,
            zoom_meeting_id=str(zoom_meeting_id) if zoom_meeting_id is not None else None,
            zoom_note_id=str(zoom_note_id) if zoom_note_id is not None else None,
            error_message=error_message,
            detail=json.dumps(detail) if detail is not None else None,
            occurred_at=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        logger.error(
            f"audit | Failed to write audit log entry for event_type={event_type}: {e}"
        )
        try:
            db.session.rollback()
        except Exception:
            pass