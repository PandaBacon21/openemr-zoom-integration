import logging
import json
from flask import request
from app.services.audit import write_audit_log
from app.models import ZoomAccount
from app.blueprints.webhooks.zoom.zoom_webhook_helpers import (_handle_url_validation, _verify_zoom_signature,
                           _handle_cn_created, _handle_waiting_room_joined, _handle_meeting_started, _handle_meeting_ended)
from app.blueprints.webhooks import webhooks_bp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Main Zoom webhook endpoint
# ---------------------------------------------------------------------------

@webhooks_bp.route("/zoom/<account_id>", methods=["POST"])
def zoom_webhook(account_id: str):
    """
    Receive and validate inbound Zoom webhook events for a specific account.

    The account_id is in the URL path so CRC validation (which carries no
    account_id in its payload) can resolve the correct webhook_secret. For
    non-CRC events the payload's account_id is cross-checked against the path.

    Flow:
      1. Look up ZoomAccount by path account_id
      2. Read raw body and parse JSON
      3. Handle endpoint.url_validation (CRC) — sign with this account's secret
      4. For non-CRC events: verify payload account_id matches path
      5. Validate signature and timestamp
      6. Route to appropriate handler
    """
    # --- 1. Look up account by path ---
    account = ZoomAccount.query.filter_by(account_id=account_id, is_active=True).first()
    if not account:
        logger.warning(f"webhooks.zoom | Unknown or inactive account in path: {account_id}")
        return {"error": "unknown account"}, 404

    # --- 2. Read raw body and parse ---
    raw_body = request.data
    if not raw_body:
        return {"error": "empty body"}, 400

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"webhooks.zoom | Failed to parse JSON: {e}")
        return {"error": "invalid JSON"}, 400

    event_type = payload.get("event")
    payload_account_id = payload.get("payload", {}).get("account_id")

    logger.info(
        f"webhooks.zoom | Received event={event_type} path_account_id={account_id} payload_account_id={payload_account_id}"
    )

    secret = account.webhook_secret
    if not secret:
        logger.warning(f"webhooks.zoom | Account {account_id} has no webhook_secret configured")
        return {"error": "webhook secret not configured"}, 500

    # --- 3. Handle CRC URL validation ---
    # CRC payloads do not include account_id — the path is the only signal.
    if event_type == "endpoint.url_validation":
        return _handle_url_validation(payload, secret)

    # --- 4. Cross-check payload account_id against path ---
    # Defense-in-depth: a valid Zoom-signed payload for account A must not be
    # accepted at account B's webhook URL.
    if payload_account_id and payload_account_id != account_id:
        logger.warning(
            f"webhooks.zoom | Account mismatch: path={account_id} payload={payload_account_id} event={event_type}"
        )
        write_audit_log(
            event_type="zoom.webhook_account_mismatch",
            success=False,
            zoom_account_id=account_id,
            detail={"event": event_type, "payload_account_id": payload_account_id},
        )
        return {"error": "account mismatch"}, 400

    # --- 5. Validate signature ---
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    signature = request.headers.get("x-zm-signature", "")

    if not timestamp or not signature:
        logger.warning("webhooks.zoom | Missing signature or timestamp headers")
        return {"error": "missing signature headers"}, 401

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
            write_audit_log(
                event_type="note.handler_error",
                success=False,
                zoom_account_id=account.account_id,
                error_message=str(e),
            )
            return {"error": "internal error"}, 500
    elif event_type == "meeting.started":
        return _handle_meeting_started(payload, account)
    elif event_type == "meeting.ended":
        return _handle_meeting_ended(payload, account)
    elif event_type in ("meeting.participant_joined_waiting_room", "meeting.participant_jbh_waiting"):
        # TODO(S13-followup): `meeting.participant_jbh_waiting` is the
        # event we actually subscribe to in the Zoom App config — it's the
        # one that reliably fires when a patient joins before the host.
        # `meeting.participant_joined_waiting_room` is kept here as a
        # safety net until further demo testing confirms it's never needed
        # under our meeting settings (join_before_host=False, waiting_room=True,
        # who_goes_to_waiting_room=users_not_in_account). Remove the
        # participant_joined_waiting_room branch once that's confirmed.
        return _handle_waiting_room_joined(payload, account)
    else:
        logger.debug(f"webhooks.zoom | Unhandled event type: {event_type}")
        return {"status": "ignored", "event": event_type}, 200
