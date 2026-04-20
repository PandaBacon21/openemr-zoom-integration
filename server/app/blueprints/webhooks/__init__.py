import hashlib
import hmac
import json

from flask import Blueprint, current_app, request

from app.services.appointment_processor import filter_appointment_event
from app.services.zoom import create_zoom_meeting
from app.extensions import db
from app.models import MeetingRecord, MeetingPatient

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")


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
        body:         Raw request bytes (request.data — untouched by Flask)
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

    current_app.logger.info(
        f"webhooks.openemr | Received appointment.set event | eid={eid} "
        f"pid={payload.get('pid')} provider_id={payload.get('provider_id')} "
        f"category_id={payload.get('category_id')}"
    )

    # --- 6. Hand off to processor ---
    return _process_appointment_event(payload)


# ---------------------------------------------------------------------------
# Event processor
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

    # S4-03: Filter
    matches = filter_appointment_event(payload)

    if not matches:
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} dropped — no matching account/provider/type"
        )
        return {"status": "dropped", "eid": eid}, 200

    current_app.logger.info(
        f"webhooks.openemr | eid={eid} matched {len(matches)} account(s), proceeding"
    )
    created_meetings = []
    errors = []
 
    for match in matches:
        account = match.zoom_account
        mapping = match.provider_mapping
 
        # S4-04: Create Zoom meeting
        try:
            meeting_data = create_zoom_meeting(match)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} account={account.account_id} "
                f"Zoom meeting creation failed: {e}"
            )
            errors.append({
                "account_id": account.account_id,
                "error": str(e)
            })
            continue
 
        # S4-05: Store MeetingRecord + MeetingPatient
        try:
            meeting_record = MeetingRecord(
                zoom_account_id=account.id,
                zoom_meeting_id=meeting_data["meeting_id"],
                zoom_start_url=meeting_data["start_url"],
                zoom_join_url=meeting_data["join_url"],
                openemr_appointment_id=str(eid),
                openemr_provider_id=str(mapping.openemr_provider_id) if mapping.openemr_provider_id else str(payload.get("provider_id")),
                openemr_appt_status=payload.get("appt_status"),
                status="created",
            )
            db.session.add(meeting_record)
            # Flush to get meeting_record.id before creating MeetingPatient
            db.session.flush()
 
            # Create MeetingPatient — one row for now, supports multiple later
            pid = payload.get("pid")
            if pid:
                meeting_patient = MeetingPatient(
                    meeting_record_id=meeting_record.id,
                    openemr_patient_id=str(pid),
                )
                db.session.add(meeting_patient)
 
            db.session.commit()
 
            current_app.logger.info(
                f"webhooks.openemr | eid={eid} account={account.account_id} "
                f"MeetingRecord created id={meeting_record.id} "
                f"zoom_meeting_id={meeting_data['meeting_id']}"
            )
 
            created_meetings.append({
                "account_id": account.account_id,
                "zoom_meeting_id": meeting_data["meeting_id"],
                "zoom_start_ulr": meeting_data["start_url"],
                "zoom_join_url": meeting_data["join_url"],
                "meeting_record_id": meeting_record.id,
            })
 
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} account={account.account_id} "
                f"DB write failed: {e}"
            )
            errors.append({
                "account_id": account.account_id,
                "error": str(e)
            })
            continue
 
    # Build response
    if not created_meetings and errors:
        # All matches failed
        return {
            "status": "error",
            "eid": eid,
            "errors": errors
        }, 500
 
    if created_meetings and errors:
        # Partial success — some matches succeeded, some failed
        return {
            "status": "partial",
            "eid": eid,
            "created": created_meetings,
            "errors": errors
        }, 207
 
    # Full success
    return {
        "status": "created",
        "eid": eid,
        "created": created_meetings,
    }, 200


# ---------------------------------------------------------------------------
# Dev/health stub
# ---------------------------------------------------------------------------

@webhooks_bp.route("/")
def index():
    return {"blueprint": "webhooks", "status": "ok"}