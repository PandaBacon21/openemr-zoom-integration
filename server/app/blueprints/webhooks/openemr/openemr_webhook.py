import logging
import json
from flask import current_app, request
from app.services.audit import write_audit_log
from app.blueprints.webhooks.openemr.openemr_webhook_helpers import _verify_signature, _process_appointment_event, _process_appointment_delete

from app.blueprints.webhooks import webhooks_bp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Main OpenEMR Webhook Endpoint
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
    secret = current_app.config.get("OPENEMR_FLASK_SECRET")
    if not secret:
        logger.error(
            "webhooks.openemr | OPENEMR_FLASK_SECRET is not configured"
        )
        return {"error": "server misconfiguration"}, 500

    # --- 2. Validate signature header is present ---
    received_sig = request.headers.get("X-Zoomly-Signature", "")
    if not received_sig:
        logger.warning(
            "webhooks.openemr | Request missing X-Zoomly-Signature header"
        )
        return {"error": "missing signature"}, 400

    # --- 3. Verify signature against raw body ---
    raw_body = request.data
    stripped_body = raw_body.strip()
    if not _verify_signature(stripped_body, received_sig, secret):
        logger.warning(
            "webhooks.openemr | Signature verification failed — possible spoofed request"
        )
        return {"error": "invalid signature"}, 401

    # --- 4. Parse JSON body ---
    try:
        payload = json.loads(stripped_body)
    except json.JSONDecodeError as e:
        logger.warning(
            f"webhooks.openemr | Failed to parse JSON body: {e}"
        )
        return {"error": "invalid JSON"}, 400

    # --- 5. Basic required field check ---
    eid = payload.get("eid")
    if not eid:
        logger.warning(
            "webhooks.openemr | Payload missing required field: eid"
        )
        return {"error": "missing required field: eid"}, 400
    
    event_type = payload.get("event")

    logger.info(
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


