import hashlib
import hmac
import time
import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from flask import current_app
from app.services.zoom import get_zoom_clinical_note
from app.services.openemr import (
    create_encounter,
    find_encounter_for_appointment,
    get_appointment_details,
    get_provider_username,
    update_appointment_status,
    write_note_to_encounter,
)
from app.services.audit import write_audit_log
from app.extensions import db, get_openemr_db_engine, scheduler
from app.models import MeetingRecord, MeetingPatient, ZoomAccount, ClinicalNoteRecord


# ---------------------------------------------------------------------------
# Helper: look up ZoomAccount by account_id from payload
# ---------------------------------------------------------------------------

def _get_account(payload: dict) -> ZoomAccount | None:
    """
    Zoom webhooks include the account_id at the top level of the payload.
    Use this to look up the correct ZoomAccount and its webhook_secret.
    """
    account_id = payload.get("account_id")
    
    # Fallback: some events nest it inside payload object
    if not account_id:
        account_id = payload.get("payload", {}).get("account_id")
    
    if not account_id:
        return None
    
    return ZoomAccount.query.filter_by(account_id=account_id, is_active=True).first()


def _get_meeting_patient_id(meeting_id: str | int) -> str | None:
    patient = MeetingPatient.query.filter_by(zoom_meeting_id=str(meeting_id)).first()
    return patient.openemr_patient_id if patient else None


# ---------------------------------------------------------------------------
# Helper: verify Zoom webhook signature
# ---------------------------------------------------------------------------

def _verify_zoom_signature(raw_body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    """
    Verify Zoom webhook signature.

    Zoom constructs the message as:
        v0:{x-zm-request-timestamp}:{raw_body_as_string}

    The raw body must be used as-is (not re-serialized) to preserve
    exact whitespace and key ordering from Zoom's request.

    Also validates the timestamp is within 5 minutes to prevent replay attacks.
    """

    # Replay attack prevention — reject requests older than 5 minutes
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            current_app.logger.warning("zoom_webhook | Timestamp out of 5-minute window, rejecting")
            return False
    except (ValueError, TypeError):
        current_app.logger.warning("zoom_webhook | Invalid timestamp header")
        return False

    message = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        secret.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Helper: handle CRC URL validation
# ---------------------------------------------------------------------------

def _handle_url_validation(payload: dict, secret: str):
    """
    Respond to Zoom's endpoint.url_validation CRC challenge.

    Zoom sends this when you click "Validate" in the app dashboard.
    Must respond within 3 seconds with the encrypted token.
    """
    plain_token = payload.get("payload", {}).get("plainToken", "")
    encrypted_token = hmac.new(
        secret.encode("utf-8"),
        msg=plain_token.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    current_app.logger.info("zoom_webhook | CRC validation challenge received, responding")
    return {
        "plainToken": plain_token,
        "encryptedToken": encrypted_token,
    }, 200


# ---------------------------------------------------------------------------
# clinical_notes async fetch
# ---------------------------------------------------------------------------

def _process_note_async(app, account_id: str, note_id: str, meeting_number: str, note_title: str | None):
    """
    Background job to fetch and write a clinical note.
    Scheduled by the webhook handler to run after a delay,
    avoiding Zoom's 3-second response timeout requirement.
    """
    with app.app_context():
        app.logger.info(f"zoom_helpers | async note job starting | note_id={note_id}")
        account = ZoomAccount.query.filter_by(account_id=account_id, is_active=True).first()
        if not account:
            app.logger.error(f"zoom_helpers | async note job | no account for {account_id}")
            write_audit_log(
                event_type="note.dropped",
                success=False,
                zoom_account_id=account_id,
                zoom_meeting_id=meeting_number,
                zoom_note_id=note_id,
                error_message="account inactive or missing at async run time",
                detail={"reason": "account_inactive"},
            )
            return
        try:
            _validate_and_process_note(
                account=account,
                meeting_number=meeting_number,
                note_id=note_id,
                note_title=note_title,
            )
        except Exception as e:
            app.logger.error(
                f"zoom_helpers | async note job | unhandled exception note_id={note_id}: {e}",
                exc_info=True,
            )
            write_audit_log(
                event_type="note.async_job_error",
                success=False,
                zoom_account_id=account.account_id,
                zoom_meeting_id=meeting_number,
                zoom_note_id=note_id,
                error_message=str(e),
            )
        app.logger.info(f"zoom_helpers | async note job complete | note_id={note_id}")


def _fetch_note_with_retry(account: ZoomAccount, note_id: str, max_attempts: int = 3, delay_seconds: int = 30) -> dict | None:
    note_data = None
    for attempt in range(1, max_attempts + 1):
        try:
            note_data = get_zoom_clinical_note(account, note_id)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            current_app.logger.error(
                f"zoom_helpers | note_id={note_id} HTTP {status} error on attempt "
                f"{attempt}/{max_attempts}: {e}"
            )
            write_audit_log(
                event_type="note.fetch_error",
                success=False,
                zoom_account_id=account.account_id,
                zoom_note_id=note_id,
                error_message=f"HTTP {status} on attempt {attempt}/{max_attempts}",
            )
            if attempt < max_attempts:
                time.sleep(delay_seconds)
            continue

        if not note_data:
            current_app.logger.warning(
                f"zoom_helpers | note_id={note_id} not found in Zoom API "
                f"(attempt {attempt}/{max_attempts})"
            )
            return None

        content = note_data.get("note_content", "")
        if content and content.strip():
            current_app.logger.info(
                f"zoom_helpers | note_id={note_id} content available "
                f"(attempt {attempt}/{max_attempts})"
            )
            if attempt > 1:
                write_audit_log(
                    event_type="note.fetched_after_retry",
                    success=True,
                    zoom_account_id=account.account_id,
                    zoom_note_id=note_id,
                    detail={"attempts": attempt, "max_attempts": max_attempts},
                )
            return note_data

        current_app.logger.warning(
            f"zoom_helpers | note_id={note_id} content empty on attempt "
            f"{attempt}/{max_attempts} — "
            + (f"retrying in {delay_seconds}s" if attempt < max_attempts else "giving up")
        )
        if attempt == max_attempts and not (content and content.strip()):
            write_audit_log(
                event_type="note.content_empty",
                success=False,
                zoom_account_id=account.account_id,
                zoom_note_id=note_id,
                error_message=f"note content empty after {max_attempts} attempts",
            )
        if attempt < max_attempts:
            time.sleep(delay_seconds)

    return note_data
# ---------------------------------------------------------------------------
# clinical_notes.note_created handler
# ---------------------------------------------------------------------------

def _handle_cn_created(payload: dict, account: ZoomAccount):
    """
    Handle clinical_notes.note_created event.
    Extracts meeting_number, note_id, and note_title from payload.
    """
    obj = payload.get("payload", {}).get("object", {})

    meeting_number = obj.get("meeting_number")
    note_id = obj.get("note_id")
    note_title = obj.get("note_title")
    ehr_context_available = obj.get("ehr_context_available", False)

    current_app.logger.info(
        f"zoom_webhook | clinical_notes.note_created | "
        f"meeting_number={meeting_number} note_id={note_id} "
        f"title='{note_title}' ehr_context={ehr_context_available}"
    )

    if not meeting_number or not note_id:
        current_app.logger.warning(
            f"zoom_webhook | clinical_notes.note_created | "
            f"Missing required fields: meeting_number={meeting_number} note_id={note_id}"
        )
        write_audit_log(
            event_type="note.received",
            success=False,
            zoom_account_id=account.account_id,
            zoom_note_id=note_id,
            error_message="missing meeting_number or note_id",
        )
        return {"error": "missing required fields"}, 400

    write_audit_log(
        event_type="note.received",
        success=True,
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_number,
        zoom_note_id=note_id,
        detail={
            "note_title": note_title,
            "ehr_context_available": ehr_context_available,
        }
    )

    # Schedule async processing — respond immediately to Zoom to avoid timeout
    app = current_app._get_current_object() # type: ignore[attr-defined]
    scheduler.add_job(
        func=_process_note_async,
        args=[app, account.account_id, note_id, str(meeting_number), note_title],
        trigger="date",
        run_date=datetime.now(timezone.utc) + timedelta(seconds=30),
        id=f"note_{note_id}",
        replace_existing=True,
        misfire_grace_time=60,
    )
    write_audit_log(
        event_type="note.processing_scheduled",
        success=True,
        zoom_account_id=account.account_id,
        zoom_meeting_id=str(meeting_number),
        zoom_note_id=note_id,
        detail={"delay_seconds": 30, "max_attempts": 3},
    )
    current_app.logger.info(
        f"zoom_helpers | note_id={note_id} scheduled for async processing at "
        f"{(datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()}"
    )

    return {"status": "accepted", "note_id": note_id}, 200


def _validate_and_process_note(
    account: ZoomAccount,
    meeting_number: str,
    note_id: str,
    note_title: str | None,
) -> tuple[dict, int]:
    """
    Validate and process a clinical note webhook event.
 
    When EHR context is available in the note (provider selected an appointment
    in Zoom), use appointment_id/patient_id/provider_id directly from the note
    rather than relying on MeetingRecord lookup.
 
    Falls back to MeetingRecord lookup when EHR context is not available.
    """
    # --- 1. Look up MeetingRecord ---
    record = MeetingRecord.query.filter_by(
        zoom_meeting_id=str(meeting_number),
        zoom_account_id=account.account_id,
    ).first()
 
    if not record:
        current_app.logger.warning(
            f"zoom_webhook | meeting_number={meeting_number} "
            f"not found in MeetingRecord — dropping note {note_id}"
        )
        write_audit_log(
            event_type="note.dropped",
            success=False,
            zoom_account_id=account.account_id,
            zoom_meeting_id=meeting_number,
            zoom_note_id=note_id,
            error_message="no matching MeetingRecord",
        )
        return {"status": "dropped", "reason": "no matching meeting"}, 200
 
    # --- 2. Persist ClinicalNoteRecord immediately ---
    clinical_note = ClinicalNoteRecord.query.filter_by(zoom_note_id=note_id).first()
    if not clinical_note:
        clinical_note = ClinicalNoteRecord(
            zoom_meeting_id=record.zoom_meeting_id,  # FK to MeetingRecord, not zoom_meeting_id
            zoom_note_id=note_id,
            zoom_note_title=note_title or "",
            is_written_to_openemr=False,
        )
        db.session.add(clinical_note)
        db.session.commit()

        record.status = "note_received"
        db.session.commit()
 
        write_audit_log(
            event_type="note.record_created",
            success=True,
            zoom_account_id=account.account_id,
            zoom_meeting_id=meeting_number,
            zoom_note_id=note_id,
        )
 
    current_app.logger.info(
        f"zoom_webhook | meeting_number={meeting_number} "
        f"matched MeetingRecord id={record.zoom_meeting_id} eid={record.openemr_appointment_id}"
    )
    record_patient_id = _get_meeting_patient_id(record.zoom_meeting_id)
 
    # --- 3. Retrieve note content from Zoom API ---
    # note_data = get_zoom_clinical_note(account, note_id)
    note_data = _fetch_note_with_retry(account, note_id, max_attempts=3, delay_seconds=30)
 
    if not note_data:
        current_app.logger.warning(
            f"zoom_webhook | note_id={note_id} not found in Zoom API"
        )
        write_audit_log(
            event_type="note.retrieved",
            success=False,
            zoom_account_id=account.account_id,
            zoom_meeting_id=meeting_number,
            zoom_note_id=note_id,
            openemr_appointment_id=str(record.openemr_appointment_id),
            openemr_provider_id=record.openemr_provider_id,
            openemr_patient_id=record_patient_id,
            error_message="note not found in Zoom API",
        )
        return {"status": "error", "reason": "note not found"}, 500
 
    # --- 4. Extract EHR context if available ---
    # When the provider selected an appointment in Zoom, the note contains
    # appointment_id, patient_id, provider_id directly — use these over
    # MeetingRecord fields to avoid encounter duplication issues.
    ehr_context = note_data.get("ehr_context")
 
    if ehr_context:
        eid         = int(ehr_context.get("appointment_id", record.openemr_appointment_id))
        pid         = int(ehr_context.get("patient_id")) if ehr_context.get("patient_id") else None
        provider_id = int(ehr_context.get("provider_id")) if ehr_context.get("provider_id") else None
        current_app.logger.info(
            f"zoom_webhook | Using EHR context: eid={eid} pid={pid} provider_id={provider_id}"
        )
    else:
        # Fall back to MeetingRecord + MeetingPatient
        eid = int(record.openemr_appointment_id)
        provider_id = int(record.openemr_provider_id) if record.openemr_provider_id else None
        pid = int(record_patient_id) if record_patient_id else None
        current_app.logger.info(
            f"zoom_webhook | No EHR context — using MeetingRecord: eid={eid} pid={pid} provider_id={provider_id}"
        )

    openemr_provider_id = str(provider_id) if provider_id is not None else None
    openemr_patient_id = str(pid) if pid is not None else None
 
    write_audit_log(
        event_type="note.retrieved",
        success=True,
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_number,
        zoom_note_id=note_id,
        openemr_appointment_id=str(eid),
        openemr_provider_id=openemr_provider_id,
        openemr_patient_id=openemr_patient_id,
        detail={
            "note_title": note_data.get("note_title"),
            "ehr_context": bool(ehr_context),
        },
    )
 
    if pid is None or provider_id is None:
        current_app.logger.warning(
            f"zoom_webhook | missing pid={pid} or provider_id={provider_id} "
            f"for MeetingRecord id={record.zoom_meeting_id}"
        )
        write_audit_log(
            event_type="note.context_missing",
            success=False,
            zoom_account_id=account.account_id,
            zoom_meeting_id=meeting_number,
            zoom_note_id=note_id,
            openemr_appointment_id=str(eid),
            openemr_provider_id=openemr_provider_id,
            openemr_patient_id=openemr_patient_id,
            error_message="missing patient or provider",
            detail={"ehr_context": bool(ehr_context)},
        )
        return {"status": "error", "reason": "missing patient or provider"}, 500
 
    # --- 5. Find existing encounter or create one ---
    encounter_number, encounter_source = find_encounter_for_appointment(eid, pid, provider_id)

    if encounter_number:
        # G-N7: surface the S7-01 fallback path in the dashboard
        if encounter_source == "manual_fallback":
            write_audit_log(
                event_type="encounter.claimed",
                success=True,
                zoom_account_id=account.account_id,
                zoom_meeting_id=meeting_number,
                zoom_note_id=note_id,
                openemr_appointment_id=str(eid),
                openemr_encounter_number=str(encounter_number),
                openemr_provider_id=openemr_provider_id,
                openemr_patient_id=openemr_patient_id,
                detail={"reason": "manual_fallback"},
            )

        # Stamp external_id if not already set (e.g. manually created encounter)
        engine = get_openemr_db_engine()
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE form_encounter
                    SET external_id = :external_id
                    WHERE encounter = :encounter
                    AND (external_id IS NULL OR external_id = '')
                """),
                {"external_id": f"zoom_eid_{eid}", "encounter": encounter_number}
            )

    if not encounter_number:
        current_app.logger.info(
            f"zoom_webhook | no encounter found for eid={eid} — creating"
        )
        appt = get_appointment_details(eid)
        if appt:
            encounter_number = create_encounter(
                pid=pid,
                provider_id=provider_id,
                facility_id=appt["facility_id"],
                pc_catid=appt["pc_catid"],
                eid=eid,
            )
            if encounter_number:
                # G-N8: explicit success audit so "encounter created, note failed" is visible
                write_audit_log(
                    event_type="encounter.created",
                    success=True,
                    zoom_account_id=account.account_id,
                    zoom_meeting_id=meeting_number,
                    zoom_note_id=note_id,
                    openemr_appointment_id=str(eid),
                    openemr_encounter_number=str(encounter_number),
                    openemr_provider_id=openemr_provider_id,
                    openemr_patient_id=openemr_patient_id,
                    detail={"trigger": "note_processing"},
                )
 
    if not encounter_number:
        current_app.logger.error(
            f"zoom_webhook | failed to find or create encounter for eid={eid}"
        )
        write_audit_log(
            event_type="note.encounter_failed",
            success=False,
            zoom_account_id=account.account_id,
            zoom_meeting_id=meeting_number,
            zoom_note_id=note_id,
            openemr_appointment_id=str(eid),
            openemr_provider_id=str(provider_id),
            openemr_patient_id=str(pid),
            error_message="could not find or create encounter",
        )
        return {"status": "error", "reason": "could not find or create encounter"}, 500
 
    current_app.logger.info(
        f"zoom_webhook | using encounter={encounter_number} for eid={eid}"
    )
 
    # --- 6. Write note to encounter ---
    async_content = note_data.get("note_content", "") or ""
    async_stripped_length = len(async_content.strip())
    async_content_blank = async_stripped_length == 0
    current_app.logger.info(
        f"zoom_webhook | note_id={note_id} encounter={encounter_number} "
        f"content_length={len(async_content)} stripped_length={async_stripped_length} "
        f"content_blank={async_content_blank}"
    )

    provider_username = get_provider_username(provider_id) or "admin"

    success = write_note_to_encounter(
        encounter_number=encounter_number,
        pid=pid,
        provider_id=provider_id,
        provider_username=provider_username,
        note_content=async_content,
        note_title=note_data.get("note_title", note_title or ""),
        note_id=note_id,
        note_writeback_mode=account.config.note_writeback_mode if account.config else "both",
    )

    if success:
        clinical_note.is_written_to_openemr = True
        clinical_note.written_to_openemr_at = datetime.now(timezone.utc)
        record.status = "note_written"
        db.session.commit()

    write_audit_log(
        event_type="note.written" if success else "note.write_failed",
        success=success,
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_number,
        zoom_note_id=note_id,
        openemr_appointment_id=str(eid),
        openemr_encounter_number=str(encounter_number),
        openemr_provider_id=str(provider_id),
        openemr_patient_id=str(pid),
        error_message=None if success else "OpenEMR note write failed",
        detail={"ehr_context": bool(ehr_context), "content_blank": async_content_blank}
    )
 
    return {
        "status": "written" if success else "write_failed",
        "encounter": encounter_number,
        "zoom_meeting_id": record.zoom_meeting_id,
    }, 200 if success else 500
 

def _handle_waiting_room_joined(payload: dict, account: ZoomAccount):
    """
    Handle meeting.participant_jbh_waiting and meeting.participant_joined_waiting_room.
    Updates appointment status to Arrived (@).
    """
    obj = payload.get("payload", {}).get("object", {})
    meeting_id = obj.get("id")
    participant_name = obj.get("participant", {}).get("user_name", "unknown")
    event_type = payload.get("event")

    current_app.logger.info(
        f"zoom_webhook | waiting_room | meeting_id={meeting_id} "
        f"participant='{participant_name}' event={event_type}"
    )

    if not meeting_id:
        current_app.logger.warning("zoom_webhook | waiting_room | missing meeting id")
        return {"error": "missing meeting id"}, 400

    # Look up MeetingRecord
    record = MeetingRecord.query.filter_by(
        zoom_meeting_id=str(meeting_id),
        zoom_account_id=account.account_id
    ).first()

    if not record:
        current_app.logger.warning(
            f"zoom_webhook | waiting_room | no MeetingRecord for meeting_id={meeting_id}"
        )
        return {"status": "no_record"}, 200

    eid = record.openemr_appointment_id
    patient_id = _get_meeting_patient_id(record.zoom_meeting_id)

    # Update appointment status to Arrived
    success = update_appointment_status(int(eid), "@")

    write_audit_log(
        event_type="appointment.patient_arrived",
        success=success,
        zoom_account_id=account.account_id,
        openemr_appointment_id=eid,
        openemr_provider_id=record.openemr_provider_id,
        openemr_patient_id=patient_id,
        zoom_meeting_id=meeting_id,
        error_message=None if success else "OpenEMR appointment status update failed",
        detail={"participant": participant_name, "trigger": event_type}
    )

    current_app.logger.info(
        f"zoom_webhook | waiting_room | eid={eid} status {'updated to Arrived' if success else 'update failed'}"
    )

    # Get appointment details for encounter creation
    appt = get_appointment_details(int(eid))
    if appt:
        encounter_number = create_encounter(
            pid=appt["pid"],
            provider_id=appt["provider_id"],
            facility_id=appt["facility_id"],
            pc_catid=appt["pc_catid"],
            eid=int(eid),
        )
        if encounter_number is None:
            current_app.logger.error(
                f"zoom_webhook | waiting_room | encounter creation failed for eid={eid}"
            )
            write_audit_log(
                event_type="encounter.create_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=str(appt["provider_id"]),
                openemr_patient_id=str(appt["pid"]),
                zoom_meeting_id=meeting_id,
                error_message="create_encounter returned None",
                detail={"trigger": "waiting_room"},
            )
        else:
            # G-N8: explicit success audit
            write_audit_log(
                event_type="encounter.created",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=str(appt["provider_id"]),
                openemr_patient_id=str(appt["pid"]),
                zoom_meeting_id=meeting_id,
                openemr_encounter_number=str(encounter_number),
                detail={"trigger": "waiting_room"},
            )

    return {"status": "ok", "eid": eid}, 200


def _handle_meeting_started(payload: dict, account: ZoomAccount):
    """
    Handle meeting.started event.
    Updates MeetingRecord status to 'started' and sets meeting_started_at.
    Used to resolve which provider is active when multiple providers share
    a Zoom user license.
    """

    obj = payload.get("payload", {}).get("object", {})
    meeting_id = str(obj.get("id", ""))
    host_id = obj.get("host_id")

    current_app.logger.info(
        f"zoom_webhook | meeting.started | meeting_id={meeting_id} host_id={host_id}"
    )

    if not meeting_id:
        current_app.logger.warning("zoom_webhook | meeting.started | missing meeting id")
        return {"error": "missing meeting id"}, 400

    record = MeetingRecord.query.filter_by(
        zoom_meeting_id=meeting_id,
        zoom_account_id=account.account_id,
    ).first()

    if not record:
        current_app.logger.warning(
            f"zoom_webhook | meeting.started | no MeetingRecord for meeting_id={meeting_id}"
        )
        return {"status": "no_record"}, 200

    record.status = "started"
    record.meeting_started_at = datetime.now(timezone.utc)
    db.session.commit()

    write_audit_log(
        event_type="meeting.started",
        success=True,
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_id,
        openemr_appointment_id=record.openemr_appointment_id,
        openemr_provider_id=record.openemr_provider_id,
    )

    current_app.logger.info(
        f"zoom_webhook | meeting.started | meeting_id={meeting_id} "
        f"provider_id={record.openemr_provider_id} status=started"
    )

    return {"status": "ok"}, 200