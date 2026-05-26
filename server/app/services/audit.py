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
      meeting.cancelled             — appointment deleted but local record preserved
                                       (detail.preserved, detail.reason set)
      meeting.create_failed         — Zoom API error during meeting creation
      meeting.update_failed         — Zoom API error during meeting update
      meeting.delete_failed         — Zoom API error during meeting delete
      meeting.started               — Zoom meeting.started webhook updated MeetingRecord
      openemr.url_writeback_success - Zoom Meeting links written to OpenEMR Appointment Record
      openemr.url_writeback_failed  - Zoom Meeting links failed when writing to OpenEMR Appointment Record
      openemr.client_enabled        — `oauth_clients.is_enabled` flipped to 1 at registration time
      openemr.client_enable_failed  — direct DB UPDATE to enable the client failed (registration rolls back)

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
      note.manual_fetch_failed  — manual fetch pre-API failure (detail.reason set;
                                  reason='encounter_locked' means the encounter
                                  or one of its Zoom-managed forms is eSign-locked)
      note.written              — note written back to OpenEMR successfully
      note.write_failed         — error writing note to OpenEMR
      note.write_skipped_locked — write refused because encounter or one of its
                                  Zoom-managed forms (SOAP / Clinical Notes) is
                                  eSign-locked. detail.lock_target identifies
                                  which: 'encounter' | 'soap' | 'clinical_notes'
                                  | 'unknown' (DB error during the lock check).
                                  detail.note_writeback_mode echoes the mode
                                  that would have been used.
      encounter.claimed         — manually-created encounter claimed via fallback path (S7-01)
      encounter.created         — new encounter created via create_encounter (detail.trigger set)
      encounter.create_failed   — create_encounter returned None (detail.trigger set)
      zoom.completion_success   — Zoom note marked complete successfully
      zoom.completion_skipped   — completion no-op for a non-error reason; check
                                  detail.reason: 'already_completed' (idempotent),
                                  'not_zoom_encounter' (eSign fired on a non-Zoom
                                  encounter), 'no_meeting_record',
                                  'no_note_on_record'
      zoom.completion_error     — error path in complete_zoom_note; check
                                  detail.reason: 'db_error',
                                  'malformed_external_id' (with detail.external_id),
                                  'no_active_account', or absent for direct Zoom
                                  API errors (error_message carries the API message)
      zoom.webhook_signature_failed — Zoom webhook signature verification failed
      zoom.webhook_account_mismatch — payload.account_id did not match the
                                       account_id in the webhook URL path
                                       (detail.event, detail.payload_account_id)

    Event types for OpenEMR auth / JWKS pipeline:
      jwks.fetched                  — /.well-known/jwks.json hit (detail.client_ip,
                                       detail.active_accounts, detail.keys_served)
      openemr.token_refresh_failed  — exchange of client assertion for access token
                                       failed in get_openemr_token (HTTPError:
                                       detail.status_code, detail.oauth_error,
                                       detail.body_snippet; otherwise detail.stage)
      openemr.token_verify_success  — UI verify endpoint succeeded
      openemr.token_verify_failed   — UI verify endpoint failed (detail.status_code
                                       when HTTPError; detail.stage="unexpected"
                                       otherwise). Pairs with token_refresh_failed
                                       on the same flow — verify_failed is the
                                       UI-level outcome, refresh_failed is the
                                       low-level token mint failure.

    Event types for Zoom auth pipeline:
      zoom.token_refresh_failed          — _fetch_zoom_token POST to
                                            zoom.us/oauth/token failed (HTTPError:
                                            detail.status_code, detail.zoom_error,
                                            detail.body_snippet; network:
                                            detail.stage="network"; otherwise
                                            detail.stage="fetch")
      zoom.credentials_validated         — registration-time validation succeeded
                                            (detail.scopes set)
      zoom.credentials_validation_failed — registration-time validation failed via
                                            HTTPError (detail.status_code set).
                                            Pairs with zoom.token_refresh_failed —
                                            credentials_validation_failed is the
                                            registration-level outcome,
                                            token_refresh_failed is the low-level
                                            HTTP failure.

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