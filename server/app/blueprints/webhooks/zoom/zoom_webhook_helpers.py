import hashlib
import hmac
import time
from datetime import datetime, timezone
from sqlalchemy import text
from flask import current_app
from app.services.zoom import get_zoom_clinical_note
from app.services.openemr import (create_encounter, get_appointment_details, 
                                  update_appointment_status, get_provider_username, find_encounter_for_appointment, 
                                  create_encounter, write_note_to_encounter, get_appointment_details)
from app.services.audit import write_audit_log
from app.extensions import db, get_openemr_db_engine
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

    # Validate meeting_number against MeetingRecord
    return _validate_and_process_note(
        account=account,
        meeting_number=meeting_number,
        note_id=note_id,
        note_title=note_title,
    )


def _validate_and_process_note(
    account: ZoomAccount,
    meeting_number: str,
    note_id: str,
    note_title: str | None,
) -> tuple[dict, int]:
    """
    Validate note's meeting_number against stored MeetingRecords.
    """
    record = MeetingRecord.query.filter_by(
        zoom_meeting_id=str(meeting_number),
        zoom_account_id=account.id,
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

    # Persist note ID immediately so we can retry later if needed
    clinical_note = ClinicalNoteRecord.query.filter_by(zoom_note_id=note_id).first()
    if not clinical_note:
        clinical_note = ClinicalNoteRecord(
            meeting_record_id=record.id,
            zoom_note_id=note_id,
            zoom_note_title=note_title or "",
            is_written_to_openemr=False,
        )
        db.session.add(clinical_note)
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
        f"matched MeetingRecord id={record.id} eid={record.openemr_appointment_id}"
    )

    # Retrieve note content from Zoom API
    note_data = get_zoom_clinical_note(account, note_id)

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
            error_message="note not found in Zoom API",
        )
        return {"status": "error", "reason": "note not found"}, 500

    write_audit_log(
        event_type="note.retrieved",
        success=True,
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_number,
        zoom_note_id=note_id,
        openemr_appointment_id=str(record.openemr_appointment_id),
        detail={"note_title": note_data.get("note_title")},
    )

    current_app.logger.info(
        f"zoom_webhook | note_id={note_id} retrieved successfully"
    )
    db.session.commit()

    # Get patient and provider from MeetingRecord
    pid = None
    patient = MeetingPatient.query.filter_by(meeting_record_id=record.id).first()
    if patient:
        pid = int(patient.openemr_patient_id)

    provider_id = int(record.openemr_provider_id) if record.openemr_provider_id else None
    eid = int(record.openemr_appointment_id)

    if not pid or not provider_id:
        current_app.logger.warning(
            f"zoom_webhook | missing pid={pid} or provider_id={provider_id} "
            f"for MeetingRecord id={record.id}"
        )
        return {"status": "error", "reason": "missing patient or provider"}, 500

    # Find existing encounter or create one
    encounter_number = find_encounter_for_appointment(eid, pid, provider_id)

    if encounter_number:
        # Ensure external_id is set for fetch_zoom_note lookup
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
            error_message="could not find or create encounter",
        )
        return {"status": "error", "reason": "could not find or create encounter"}, 500

    current_app.logger.info(
        f"zoom_webhook | S5-05 | using encounter={encounter_number} for eid={eid}"
    )

    # Get provider username for forms.user field
    provider_username = get_provider_username(provider_id) or "admin"

    # Write note to encounter
    success = write_note_to_encounter(
        encounter_number=encounter_number,
        pid=pid,
        provider_id=provider_id,
        provider_username=provider_username,
        note_content=note_data.get("note_content", ""),
        note_title=note_data.get("note_title", note_title or ""),
        note_id=note_id,
    )
    if success:
        clinical_note.is_written_to_openemr = True
        clinical_note.written_to_openemr_at = datetime.now(timezone.utc)
        
        db.session.commit()

    write_audit_log(
        event_type="note.written" if success else "note.write_failed",
        success=success,
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_number,
        zoom_note_id=note_id,
        openemr_appointment_id=str(eid),
        detail={"encounter": encounter_number}
    )

    return {
        "status": "written" if success else "write_failed",
        "encounter": encounter_number,
        "meeting_record_id": record.id,
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
        zoom_account_id=account.id
    ).first()

    if not record:
        current_app.logger.warning(
            f"zoom_webhook | waiting_room | no MeetingRecord for meeting_id={meeting_id}"
        )
        return {"status": "no_record"}, 200

    eid = record.openemr_appointment_id

    # Update appointment status to Arrived
    success = update_appointment_status(int(eid), "@")

    write_audit_log(
        event_type="appointment.patient_arrived",
        success=success,
        zoom_account_id=account.account_id,
        openemr_appointment_id=eid,
        zoom_meeting_id=meeting_id,
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

    return {"status": "ok", "eid": eid}, 200
