import logging
import json
from flask import request
from app.services.audit import write_audit_log
from app.models import ZoomAccount
from app.blueprints.webhooks.zoom.zoom_webhook_helpers import (_get_account, _handle_url_validation, _verify_zoom_signature, 
                           _handle_cn_created, _handle_waiting_room_joined, _handle_meeting_started)
from app.blueprints.webhooks import webhooks_bp

logger = logging.getLogger(__name__)

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
        logger.warning(f"webhooks.zoom | Failed to parse JSON: {e}")
        return {"error": "invalid JSON"}, 400

    event_type = payload.get("event")
    account_id = payload.get("payload", {}).get("account_id")

    logger.info(
        f"webhooks.zoom | Received event={event_type} account_id={account_id}"
    )

   # --- 3. Handle CRC URL validation first ---
    # CRC requests have no account_id — match against first active account
    if event_type == "endpoint.url_validation":
        # Try account lookup, fall back to first active account
        account = _get_account(payload) or ZoomAccount.query.filter_by(is_active=True).first()
        if not account:
            logger.warning("webhooks.zoom | CRC received but no active account found")
            return {"error": "unknown account"}, 404
        secret = account.webhook_secret
        if not secret:
            logger.warning("webhooks.zoom | CRC received but no webhook_secret configured")
            return {"error": "webhook secret not configured"}, 500
        return _handle_url_validation(payload, secret)

    # --- 4. Look up ZoomAccount for all other events ---
    account = _get_account(payload)
    if not account:
        logger.warning(f"webhooks.zoom | No active account found for account_id={account_id}")
        return {"error": "unknown account"}, 404

    # --- 5. Validate signature ---
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    signature = request.headers.get("x-zm-signature", "")

    if not timestamp or not signature:
        logger.warning("webhooks.zoom | Missing signature or timestamp headers")
        return {"error": "missing signature headers"}, 401

    secret = account.webhook_secret
    if not secret:
        logger.warning(f"webhooks.zoom | Account {account_id} has no webhook_secret configured")
        return {"error": "webhook secret not configured"}, 500

    if not _verify_zoom_signature(raw_body, timestamp, signature, secret):
        logger.warning(f"webhooks.zoom | Invalid signature for account={account_id} event={event_type}")
        write_audit_log(
            event_type="zoom.webhook_signature_failed",
            success=False,
            zoom_account_id=account_id,
            detail={"event": event_type}
        )
        return {"error": "invalid signature"}, 401

    logger.info(
        f"webhooks.zoom | Signature verified for account={account_id} event={event_type}"
    )

    # --- 6. Route to handler ---
    if event_type == "clinical_notes.note_created":
        try:
            return _handle_cn_created(payload, account)
        except Exception as e:
            logger.error(f"webhooks.zoom | Unhandled exception in _handle_cn_created: {e}", exc_info=True)
            return {"error": "internal error"}, 500
    elif event_type == "meeting.started":
        return _handle_meeting_started(payload, account)
    elif event_type in ("meeting.participant_joined_waiting_room", "meeting.participant_jbh_waiting"):
        return _handle_waiting_room_joined(payload, account)
    else:
        logger.debug(f"webhooks.zoom | Unhandled event type: {event_type}")
        return {"status": "ignored", "event": event_type}, 200
