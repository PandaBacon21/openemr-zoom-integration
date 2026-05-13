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
    openemr_encounter_number: str | None = None,
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
      appointment.dropped           — filtered out (detail.reason: missing_provider_id,
                                       provider_unmapped, account_inactive, type_mismatch)
      appointment.delete_no_record  — delete event received but no MeetingRecord existed
      appointment.patient_arrived   — waiting-room/JBH event marked appt as Arrived
      meeting.created               — Zoom meeting created successfully
      meeting.updated               — Zoom meeting patched with new appointment details
      meeting.recreated             — replacement meeting created after Zoom deletion
      meeting.deleted               — Zoom meeting deleted on appointment delete
      meeting.create_failed         — Zoom API error during meeting creation
      meeting.update_failed         — Zoom API error during meeting update
      meeting.delete_failed         — Zoom API error during meeting delete
      meeting.started               — Zoom meeting.started webhook updated MeetingRecord
      openemr.url_writeback_success - Zoom Meeting links written to OpenEMR Appointment Record
      openemr.url_writeback_failed  - Zoom Meeting links failed when writing to OpenEMR Appointment Record

    Event types for clinical note pipeline:
      note.received             — clinical note webhook received from Zoom
      note.processing_scheduled - note retrieval process scheduled in background process
      note.retrieved            — note content fetched from Zoom API
      note.fetch_error          — Zoom API HTTP error during fetch attempt
      note.fetched_after_retry  — non-empty content arrived on attempt > 1 (Zoom race)
      note.content_empty        — note content empty/whitespace at fetch time
      note.context_missing      — pid or provider_id missing for note write
      note.encounter_failed     — could not find or create encounter for note
      note.dropped              — webhook received but no matching MeetingRecord
                                  (also: async job runs but account is inactive)
      note.record_created       — ClinicalNoteRecord persisted on first webhook arrival
      note.handler_error        — top-level exception in clinical_notes.note_created handler
      note.async_job_error      — unhandled exception inside async note processor
      note.manual_fetch_requested — manual fetch button pressed in OpenEMR UI
      note.manual_fetch_failed  — manual fetch pre-API failure (detail.reason set)
      note.written              — note written back to OpenEMR successfully
      note.write_failed         — error writing note to OpenEMR
      encounter.claimed         — manually-created encounter claimed via fallback path (S7-01)
      encounter.created         — new encounter created via create_encounter (detail.trigger set)
      encounter.create_failed   — create_encounter returned None (detail.trigger set)
      zoom.completion_success   — Zoom meeting marked complete successfully
      zoom.completion_skipped   — completion idempotent — already marked complete
      zoom.completion_error     — error marking Zoom meeting complete
      zoom.webhook_signature_failed — Zoom webhook signature verification failed

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
            openemr_encounter_number=str(openemr_encounter_number) if openemr_encounter_number is not None else None,
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