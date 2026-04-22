import hashlib
import hmac
import json

from flask import Blueprint, current_app, request

from app.services.appointment_processor import filter_appointment_event
from app.services.zoom import create_zoom_meeting, get_zoom_meeting, delete_zoom_meeting
from app.services.audit import write_audit_log
from app.extensions import db
from app.models import MeetingRecord, MeetingPatient, ZoomAccount

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")

"""
OPENEMR WEBHOOK
"""

# ---------------------------------------------------------------------------
# Signature verification helper
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, received_sig: str, secret: str) -> bool:
    """
    Recompute HMAC-SHA256 over the raw request body and compare
    against the signature sent in the X-Zoomly-Signature header.

    Uses hmac.compare_digest() for a timing-safe comparison —
    prevents timing attacks that could leak the secret one bit at a time.

    Args:
        body:         Raw request bytes (request.data)
        received_sig: Hex digest from the X-Zoomly-Signature header
        secret:       OPENEMR_WEBHOOK_SECRET from app config

    Returns:
        True if signatures match, False otherwise.
    """
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, received_sig)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@webhooks_bp.route("/openemr", methods=["POST"])
def openemr_appointment_webhook():
    """
    Receives appointment.set events from OpenEMR's PHP listener module.

    Request contract:
      - Content-Type: application/json
      - Header X-Zoomly-Signature: <hmac-sha256 hex of raw body>
      - Body: JSON payload defined in AppointmentListener.php

    Response:
      - 200: event accepted (or intentionally dropped — see filter logic)
      - 400: malformed request (missing header, bad JSON)
      - 401: signature mismatch
      - 500: unexpected error during processing
    """
    # --- 1. Pull secret from config ---
    secret = current_app.config.get("OPENEMR_WEBHOOK_SECRET")
    if not secret:
        current_app.logger.error(
            "webhooks.openemr | OPENEMR_WEBHOOK_SECRET is not configured"
        )
        return {"error": "server misconfiguration"}, 500

    # --- 2. Validate signature header is present ---
    received_sig = request.headers.get("X-Zoomly-Signature", "")
    if not received_sig:
        current_app.logger.warning(
            "webhooks.openemr | Request missing X-Zoomly-Signature header"
        )
        return {"error": "missing signature"}, 400

    # --- 3. Verify signature against raw body ---
    raw_body = request.data
    stripped_body = raw_body.strip()
    if not _verify_signature(stripped_body, received_sig, secret):
        current_app.logger.warning(
            "webhooks.openemr | Signature verification failed — possible spoofed request"
        )
        return {"error": "invalid signature"}, 401

    # --- 4. Parse JSON body ---
    try:
        payload = json.loads(stripped_body)
    except json.JSONDecodeError as e:
        current_app.logger.warning(
            f"webhooks.openemr | Failed to parse JSON body: {e}"
        )
        return {"error": "invalid JSON"}, 400

    # --- 5. Basic required field check ---
    eid = payload.get("eid")
    if not eid:
        current_app.logger.warning(
            "webhooks.openemr | Payload missing required field: eid"
        )
        return {"error": "missing required field: eid"}, 400
    
    event_type = payload.get("event")

    current_app.logger.info(
        f"webhooks.openemr | Received {event_type} event | eid={eid} "
        f"pid={payload.get('pid')} provider_id={payload.get('provider_id')} "
        f"category_id={payload.get('category_id')}"
    )

    write_audit_log(
        event_type=f"appointment.received.{event_type}" if event_type else "appointment.received",
        success=True,
        openemr_appointment_id=eid,
        detail={"event": event_type, "appointment_type": payload.get("category_id")},
    )

    # --- 6. Hand off to appropriate handler ---
    if event_type == "appointment.deleted":
        return _process_appointment_delete(payload)
    else:
        return _process_appointment_event(payload)


# ---------------------------------------------------------------------------
# Create/Update handler
# ---------------------------------------------------------------------------

def _process_appointment_event(payload: dict) -> tuple[dict, int]:
    """
    Orchestrates the appointment event pipeline:
      S4-03: Filter — check provider mapping + appointment type mapping  ✓
      S4-04: Zoom API — create meeting with provider as host             ✓
      S4-05: Store MeetingRecord + MeetingPatient                        ✓
      S4-06: Error handling
      S4-07: Write AuditLog entry

    Args:
        payload: Validated, parsed appointment event dict from OpenEMR.

    Returns:
        (response_body_dict, http_status_code)
    """
    eid = payload.get("eid")

    # Filter
    matches = filter_appointment_event(payload)

    if not matches:
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} dropped — no matching account/provider/type"
        )
        write_audit_log(
            event_type="appointment.dropped",
            success=True,
            openemr_appointment_id=eid,
            detail={"reason": "no matching provider/type", "appointment_type": payload.get("category_id")},
        )
        return {"status": "dropped", "eid": eid}, 200

    current_app.logger.info(
        f"webhooks.openemr | eid={eid} matched {len(matches)} account(s), proceeding"
    )
    created_meetings = []
    updated_meetings = []
    errors = []
 
    for match in matches:
        account = match.zoom_account
        # mapping = match.provider_mapping

        # Check for existing MeetingRecord
        existing_meeting_record = MeetingRecord.query.filter_by(
            openemr_appointment_id=str(eid),
            zoom_account_id=account.id
        ).first()

        if existing_meeting_record:
            # Update path
            result = _handle_existing_meeting(
                existing_meeting_record, match, payload
            )
            if result.get("error"):
                errors.append({
                    "account_id": account.account_id,
                    "error": result["error"]
                })
            else:
                updated_meetings.append(result)
        else:
            # Create path
            result = _handle_new_meeting(match, payload)
            if result.get("error"):
                errors.append({
                    "account_id": account.account_id,
                    "error": result["error"]
                })
            else:
                created_meetings.append(result)
 
    # Build response
    if not created_meetings and not updated_meetings and errors:
        return {"status": "error", "eid": eid, "errors": errors}, 500
 
    if (created_meetings or updated_meetings) and errors:
        return {
            "status": "partial",
            "eid": eid,
            "created": created_meetings,
            "updated": updated_meetings,
            "errors": errors
        }, 207
 
    return {
        "status": "ok",
        "eid": eid,
        "created": created_meetings,
        "updated": updated_meetings,
    }, 200
 
 
def _handle_new_meeting(match, payload: dict) -> dict:
    """Create a new Zoom meeting and MeetingRecord."""
    account = match.zoom_account
    mapping = match.provider_mapping
    eid = payload.get("eid")
 
    try:
        meeting_data = create_zoom_meeting(match)
    except Exception as e:
        current_app.logger.error(
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"Zoom meeting creation failed: {e}"
        )
        return {"error": str(e)}
 
    try:
        meeting_record = MeetingRecord(
            zoom_account_id=account.id,
            zoom_meeting_id=meeting_data["meeting_id"],
            zoom_start_url=meeting_data["start_url"],
            zoom_join_url=meeting_data["join_url"],
            openemr_appointment_id=str(eid),
            openemr_provider_id=str(mapping.openemr_provider_id),
            openemr_appt_status=payload.get("appt_status"),
            status="created",
        )
        db.session.add(meeting_record)
        db.session.flush()
 
        pid = payload.get("pid")
        if pid:
            db.session.add(MeetingPatient(
                meeting_record_id=meeting_record.id,
                openemr_patient_id=str(pid),
            ))
 
        db.session.commit()
 
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"MeetingRecord created id={meeting_record.id} "
            f"zoom_meeting_id={meeting_data['meeting_id']}"
        )
        write_audit_log(
            event_type="meeting.created",
            success=True,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_provider_id=mapping.openemr_provider_id,
            zoom_meeting_id=meeting_data["meeting_id"],
        )

        # Write Zoom URLs back to OpenEMR appointment record
        from app.services.openemr import write_zoom_urls_to_appointment
        if eid:
            success = write_zoom_urls_to_appointment(
                eid=eid,
                start_url=meeting_data["start_url"],
                join_url=meeting_data["join_url"],
            )

            current_app.logger.info(
                f"webhooks.openemr | eid={eid} account={account.account_id} "
                f"{'Meeting link written back to OpenEMR' if success else 'Meeting link failed to write back to OpenEMR'} "
                f"zoom_meeting_id={meeting_data['meeting_id']}"
            )

            write_audit_log(
                event_type="openemr.url_writeback_success" if success else "openemr.url_writeback_failed",
                success=success,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_data["meeting_id"],
            )   
 
        return {
            "account_id": account.account_id,
            "zoom_meeting_id": meeting_data["meeting_id"],
            "zoom_join_url": meeting_data["join_url"],
            "zoom_start_url": meeting_data["start_url"],
            "meeting_record_id": meeting_record.id,
        }
 
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"DB write failed: {e}"
        )
        write_audit_log(
            event_type="meeting.create_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            error_message=str(e),
        )

        return {"error": str(e)}
 
 
def _handle_existing_meeting(
    record: MeetingRecord,
    match,
    payload: dict
) -> dict:
    """
    Handle an appointment event when a MeetingRecord already exists.
 
    Checks if the Zoom meeting still exists:
    - If deleted in Zoom → create a new meeting, update the record
    - If exists → patch the meeting with updated fields, update the record
    """
    account = match.zoom_account
    eid = payload.get("eid")
 
    current_app.logger.info(
        f"webhooks.openemr | eid={eid} existing MeetingRecord id={record.id} "
        f"zoom_meeting_id={record.zoom_meeting_id} — checking Zoom"
    )
 
    # Check if meeting still exists in Zoom
    try:
        zoom_meeting = get_zoom_meeting(account, record.zoom_meeting_id)
    except Exception as e:
        current_app.logger.error(
            f"webhooks.openemr | eid={eid} failed to check Zoom meeting "
            f"{record.zoom_meeting_id}: {e}"
        )
        return {"error": str(e)}
 
    if zoom_meeting is None:
        # Meeting was deleted in Zoom — create a new one
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} Zoom meeting {record.zoom_meeting_id} "
            "no longer exists — creating replacement"
        )
        try:
            meeting_data = create_zoom_meeting(match)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} replacement meeting creation failed: {e}"
            )
            return {"error": str(e)}
 
        try:
            record.zoom_meeting_id = meeting_data["meeting_id"]
            record.zoom_start_url = meeting_data["start_url"]
            record.zoom_join_url = meeting_data["join_url"]
            record.openemr_appt_status = payload.get("appt_status")
            record.status = "created"
            db.session.commit()
 
            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord id={record.id} "
                f"updated with new zoom_meeting_id={meeting_data['meeting_id']}"
            )
            write_audit_log(
                event_type="meeting.recreated",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_data["meeting_id"],
            )

            # Write new URLs back to OpenEMR appointment record
            from app.services.openemr import write_zoom_urls_to_appointment
            if eid:
                success = write_zoom_urls_to_appointment(
                    eid=eid,
                    start_url=meeting_data["start_url"],
                    join_url=meeting_data["join_url"],
                )

                current_app.logger.info(
                    f"webhooks.openemr | eid={eid} account={account.account_id} "
                    f"{'Meeting link written back to OpenEMR' if success else 'Meeting link failed to write back to OpenEMR'} "
                    f"zoom_meeting_id={meeting_data['meeting_id']}"
                )

                write_audit_log(
                    event_type="openemr.url_writeback_success" if success else "openemr.url_writeback_failed",
                    success=success,
                    zoom_account_id=account.account_id,
                    openemr_appointment_id=eid,
                    zoom_meeting_id=meeting_data["meeting_id"],
                )
 
            return {
                "account_id": account.account_id,
                "zoom_meeting_id": meeting_data["meeting_id"],
                "zoom_join_url": meeting_data["join_url"],
                "zoom_start_url": meeting_data["start_url"],
                "meeting_record_id": record.id,
                "action": "recreated",
            }
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}
 
    else:
        # Meeting exists — patch it with updated fields
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} Zoom meeting {record.zoom_meeting_id} "
            "exists — updating"
        )
        try:
            from app.services.zoom import update_zoom_meeting
            update_zoom_meeting(account, record.zoom_meeting_id, match)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} failed to update Zoom meeting "
                f"{record.zoom_meeting_id}: {e}"
            )
            return {"error": str(e)}
 
        try:
            record.openemr_appt_status = payload.get("appt_status")
            db.session.commit()
 
            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord id={record.id} updated"
            )
            write_audit_log(
                event_type="meeting.updated",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=record.zoom_meeting_id,
            )
 
            return {
                "account_id": account.account_id,
                "zoom_meeting_id": record.zoom_meeting_id,
                "zoom_join_url": record.zoom_join_url,
                "zoom_start_url": record.zoom_start_url,
                "meeting_record_id": record.id,
                "action": "updated",
            }
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}
 

# ---------------------------------------------------------------------------
# Delete handler
# ---------------------------------------------------------------------------
 
def _process_appointment_delete(payload: dict) -> tuple[dict, int]:
    """
    Handle appointment.deleted events from OpenEMR.
 
    Looks up MeetingRecord by eid, deletes the Zoom meeting,
    and removes the local record.
    """
    eid = payload.get("eid")
 
    # Find all meeting records for this appointment
    # (could be multiple if multi-account, but typically one)
    records = MeetingRecord.query.filter_by(
        openemr_appointment_id=str(eid)
    ).all()
 
    if not records:
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} delete event received but no MeetingRecord found — nothing to do"
        )
        return {"status": "no_record", "eid": eid}, 200
 
    deleted_meetings = []
    errors = []
 
    for record in records:
        account = record.zoom_account
        meeting_id = record.zoom_meeting_id
 
        # Delete from Zoom
        try:
            delete_zoom_meeting(account, meeting_id)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} failed to delete Zoom meeting "
                f"{meeting_id}: {e}"
            )
            errors.append({"meeting_id": meeting_id, "error": str(e)})
            # Mark record as error but continue — still remove from DB
            record.status = "error"
            db.session.commit()
            continue
 
        # Remove from DB — cascade deletes MeetingPatient rows
        try:
            db.session.delete(record)
            db.session.commit()
            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord id={record.id} "
                f"and Zoom meeting {meeting_id} deleted"
            )
            write_audit_log(
                event_type="meeting.deleted",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_id,
            )
            deleted_meetings.append(meeting_id)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} failed to delete MeetingRecord "
                f"id={record.id}: {e}"
            )
            write_audit_log(
                event_type="meeting.delete_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_id,
                error_message=str(e),
            )
            errors.append({"meeting_id": meeting_id, "error": str(e)})
 
    if errors and not deleted_meetings:
        return {"status": "error", "eid": eid, "errors": errors}, 500
 
    return {
        "status": "deleted",
        "eid": eid,
        "deleted_meetings": deleted_meetings
    }, 200


"""
ZOOM WEBHOOK
"""


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
    import time

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
# Main Zoom webhook endpoint
# ---------------------------------------------------------------------------

@webhooks_bp.route("/zoom", methods=["POST"])
def zoom_webhook():
    """
    S5-01: Receive and validate inbound Zoom webhook events.

    Flow:
      1. Read raw body (critical — must not use request.json)
      2. Parse JSON to get account_id and event type
      3. Look up ZoomAccount by account_id
      4. Handle endpoint.url_validation (CRC) without full sig check
      5. Validate signature and timestamp
      6. Route to appropriate handler
    """
    # --- 1. Read raw body ---
    raw_body = request.data
    if not raw_body:
        return {"error": "empty body"}, 400

    # --- 2. Parse payload ---
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError) as e:
        current_app.logger.warning(f"zoom_webhook | Failed to parse JSON: {e}")
        return {"error": "invalid JSON"}, 400

    event_type = payload.get("event")
    account_id = payload.get("payload", {}).get("account_id")

    current_app.logger.info(
        f"zoom_webhook | Received event={event_type} account_id={account_id}"
    )

   # --- 3. Handle CRC URL validation first ---
    # CRC requests have no account_id — match against first active account
    if event_type == "endpoint.url_validation":
        # Try account lookup, fall back to first active account
        account = _get_account(payload) or ZoomAccount.query.filter_by(is_active=True).first()
        if not account:
            current_app.logger.warning("zoom_webhook | CRC received but no active account found")
            return {"error": "unknown account"}, 404
        secret = account.webhook_secret
        if not secret:
            current_app.logger.warning("zoom_webhook | CRC received but no webhook_secret configured")
            return {"error": "webhook secret not configured"}, 500
        return _handle_url_validation(payload, secret)

    # --- 4. Look up ZoomAccount for all other events ---
    account = _get_account(payload)
    if not account:
        current_app.logger.warning(f"zoom_webhook | No active account found for account_id={account_id}")
        return {"error": "unknown account"}, 404

    # --- 5. Validate signature ---
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    signature = request.headers.get("x-zm-signature", "")

    if not timestamp or not signature:
        current_app.logger.warning("zoom_webhook | Missing signature or timestamp headers")
        return {"error": "missing signature headers"}, 401

    secret = account.webhook_secret
    if not secret:
        current_app.logger.warning(f"zoom_webhook | Account {account_id} has no webhook_secret configured")
        return {"error": "webhook secret not configured"}, 500

    if not _verify_zoom_signature(raw_body, timestamp, signature, secret):
        current_app.logger.warning(f"zoom_webhook | Invalid signature for account={account_id} event={event_type}")
        write_audit_log(
            event_type="zoom.webhook_signature_failed",
            success=False,
            zoom_account_id=account_id,
            detail={"event": event_type}
        )
        return {"error": "invalid signature"}, 401

    current_app.logger.info(
        f"zoom_webhook | Signature verified for account={account_id} event={event_type}"
    )

    # --- 6. Route to handler ---
    if event_type == "clinical_notes.note_created":
        return _handle_cn_created(payload, account)
    else:
        current_app.logger.debug(f"zoom_webhook | Unhandled event type: {event_type}")
        return {"status": "ignored", "event": event_type}, 200

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

    current_app.logger.info(
        f"zoom_webhook | meeting_number={meeting_number} "
        f"matched MeetingRecord id={record.id} eid={record.openemr_appointment_id}"
    )

    # Retrieve note content from Zoom API
    from app.services.zoom import get_zoom_clinical_note
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
            error_message="note not found in Zoom API",
        )
        return {"status": "error", "reason": "note not found"}, 500

    write_audit_log(
        event_type="note.retrieved",
        success=True,
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_number,
        zoom_note_id=note_id,
        detail={"note_title": note_data.get("note_title")}
    )

    current_app.logger.info(
        f"zoom_webhook | note_id={note_id} retrieved successfully"
    )

    # S5-05 placeholder: write note to OpenEMR
    return {"status": "received", "meeting_record_id": record.id}, 200


# ---------------------------------------------------------------------------
# Dev/health stub
# ---------------------------------------------------------------------------

@webhooks_bp.route("/")
def index():
    return {"blueprint": "webhooks", "status": "ok"}
