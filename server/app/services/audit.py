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
    openemr_user_id: str | None = None,
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
      note.processing_scheduled - note retrieval handed off to APScheduler. detail
                                  fields: initial_delay_seconds (0 = run immediately,
                                  default for Zoom's current behavior),
                                  retry_delay_seconds (interval between attempts when
                                  empty content is served), max_attempts
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

    Event types for Epic-ZCC CTI middleware (Sprint 11):
      epic_zcc.jwks_fetched         — GET /oauth2/keys/<version>/<kid> served
                                       a single-key JWKS to Zoom.
                                       detail.client_ip, detail.kid, detail.version
      epic_zcc.token_issued         — POST /oauth2/token minted an opaque
                                       access token. detail.iss, detail.jti,
                                       detail.expires_in
      epic_zcc.token_request_failed — token issuance refused. detail.reason:
                                       'bad_request' | 'kid_missing' |
                                       'alg_unsupported' | 'jku_untrusted' |
                                       'jwks_fetch_failed' | 'bad_signature' |
                                       'expired' | 'replay' | 'aud_mismatch' |
                                       'iss_sub_mismatch'
      epic_zcc.bearer_token_invalid — protected endpoint (PatientLookUp /
                                       Practitioner / ReceiveCommunication3)
                                       rejected a bearer token. detail.reason:
                                       'missing_header' | 'expired_or_unknown' |
                                       'account_mismatch' (with
                                       detail.path_account_id)
      epic_zcc.patient_lookup_received  — POST PatientLookUp(2012) parsed.
                                           openemr_user_id = <UserID>;
                                           detail.criteria_fields lists which
                                           inputs were present;
                                           detail.patient_id_type set when
                                           PatientID is in play.
      epic_zcc.patient_lookup_resolved  — OR-search completed.
                                           detail.match_count,
                                           detail.queried_fields (which criterion
                                           keys actually generated SQL; not a
                                           confidence ranking — Zoom decides order).
      epic_zcc.patient_lookup_failed    — request refused. detail.reason:
                                           'empty_body' | 'malformed_xml' |
                                           'missing_user' | 'insufficient_criteria' |
                                           'db_error'. detail.fault_code carries
                                           the Epic-shaped fault code returned to ZCC.
      epic_zcc.practitioner_lookup_received — GET Practitioner.Search parsed.
                                                detail.search_type:
                                                'identifier' | '_id' | 'name' |
                                                'family'; detail.query_fields
                                                lists the request parameters used.
      epic_zcc.practitioner_lookup_resolved — OpenEMR provider search completed.
                                                detail.match_count.
      epic_zcc.practitioner_lookup_failed   — request refused or search failed.
                                                detail.reason:
                                                'missing_search_parameters' |
                                                'invalid_identifier' |
                                                'given_without_family' |
                                                'invalid_count' | 'db_error'.
                                                detail.fhir_error_code carries
                                                the FHIR error code returned.
      epic_zcc.receive_communication_received — POST ReceiveCommunication3 parsed.
                                                 detail.recipient_id,
                                                 detail.patient_id_type,
                                                 detail.has_patient_id,
                                                 detail.communication_type,
                                                 detail.call_id.
      epic_zcc.receive_communication_pushed   — cached PatientLookUp row matched
                                                 and an SSE event was pushed to at
                                                 least one OpenEMR subscriber.
                                                 detail.recipient_id,
                                                 detail.subscriber_count,
                                                 detail.matched_on.
      epic_zcc.receive_communication_failed   — screen-pop dispatch refused or
                                                 skipped. Routes still ack ZCC for
                                                 business misses so the connected
                                                 call is not retried. detail.reason:
                                                 'malformed_body' |
                                                 'missing_recipient' |
                                                 'unknown_agent' |
                                                 'mapping_missing_openemr_user' |
                                                 'no_cached_lookup' |
                                                 'missing_patient_id' |
                                                 'patient_not_in_cache' |
                                                 'no_subscribers' | 'db_error' |
                                                 'handler_error'.

    Event types for demo data hydration (Sprint 13):
      demo.hydrate_started          — Hydrate Demo Data orchestrator started
                                       for an account
      demo.hydrate_completed        — orchestrator finished; detail.summary
                                       carries counts (providers_processed,
                                       appointments_created, meetings_created,
                                       meetings_backfilled, past_encounters_created,
                                       errors[])
      demo.hydrate_request_failed   — top-level failure in /config/demo/hydrate
                                       endpoint (validation or unexpected
                                       exception before/around orchestrator)
      demo.hydrate_provider_skipped — provider skipped during orchestration.
                                       detail.reason: 'unknown_specialty' |
                                       'no_matching_categories' | 'no_patients'
      demo.future_appointment_created       — appointment row inserted by
                                                generate_future_appointment
                                                (detail.slot, detail.category_id)
      demo.future_appointment_create_failed — appointment insert failed
                                                (detail.stage,
                                                detail.openemr_user_id)
      demo.future_meeting_created    — Zoom meeting created for a newly-
                                        generated future appointment
      demo.future_meeting_backfilled — Zoom meeting added to an existing
                                        appointment that lacked one (re-run
                                        scenario)
      demo.past_encounter_seeded    — historical locked encounter + sample
                                       note seeded for a provider's patient
                                       (detail.openemr_user_id,
                                       detail.openemr_patient_id, detail.eid)
      demo.past_encounter_skipped   — past-encounter seed skipped.
                                       detail.reason: 'unknown_specialty' |
                                       'no_patients' | 'category_missing_in_openemr'
                                       | '8am_slot_occupied'
      demo.past_encounter_failed    — error during past-encounter seed.
                                       detail.stage: 'create_appointment' |
                                       'create_encounter' | 'write_note'

    Args:
        event_type:               One of the event type strings above
        success:                  Whether the operation succeeded
        zoom_account_id:          Zoom account ID string (not internal PK)
        openemr_appointment_id:   OpenEMR appointment eid
        openemr_user_id:      OpenEMR provider users.id
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
            openemr_user_id=str(openemr_user_id) if openemr_user_id is not None else None,
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
