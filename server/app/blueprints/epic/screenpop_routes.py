"""OpenEMR-facing screen-pop bootstrap and SSE stream routes."""

import json
import logging
import time
from queue import Empty
from urllib.parse import urlencode

from flask import Response, current_app, g, jsonify, request

from app.blueprints.epic import epic_bp, epic_openemr_bp
from app.models import AccountConfig, UserMapping, ZoomAccount
from app.services.audit import write_audit_log
from app.services.epic.constants import EPIC_SCREENPOP_TOKEN_TTL_SECONDS
from app.services.epic.screenpop_auth import (
    ScreenpopTokenError,
    make_screenpop_token,
    verify_bridge_signature,
    verify_screenpop_token,
)
from app.services.epic.screenpop_dispatch import subscribe, unsubscribe


logger = logging.getLogger(__name__)

_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
_SSE_CONTENT_TYPE = "text/event-stream; charset=utf-8"
_KEEPALIVE_SECONDS = 15


@epic_openemr_bp.route("/screenpop/bootstrap", methods=["POST"])
def screenpop_bootstrap():
    """Return account-scoped SSE stream URLs for the logged-in OpenEMR user.

    OpenEMR PHP calls this server-to-server using the existing ZoomBridge HMAC
    signature. The browser never receives an account id from env; it only gets
    the stream URLs for accounts where this OpenEMR user is actively mapped as
    a ZCC agent.
    """
    secret = current_app.config.get("OPENEMR_FLASK_SECRET")
    if not secret:
        logger.error("epic.screenpop_bootstrap | OPENEMR_FLASK_SECRET not configured")
        _audit_screenpop_failure("missing_secret", None, None, error_message="missing secret")
        return jsonify({"error": "server misconfiguration"}), 500

    raw_body = request.get_data()
    received_signature = request.headers.get("X-Zoomly-Signature", "")
    if not received_signature:
        _audit_screenpop_failure("missing_signature", None, None)
        return jsonify({"error": "missing signature"}), 401
    if not verify_bridge_signature(raw_body, received_signature, secret):
        _audit_screenpop_failure("invalid_signature", None, None)
        return jsonify({"error": "invalid signature"}), 401

    try:
        payload = json.loads(raw_body.strip() or b"{}")
    except json.JSONDecodeError as e:
        _audit_screenpop_failure("malformed_body", None, None, error_message=str(e))
        return jsonify({"error": "invalid JSON"}), 400

    openemr_user_id = str(payload.get("openemr_user_id") or "").strip()
    if not openemr_user_id:
        _audit_screenpop_failure("missing_openemr_user", None, None)
        return jsonify({"error": "missing openemr_user_id"}), 400

    mappings = _active_agent_mappings_for_user(openemr_user_id)
    streams = [
        _build_stream_descriptor(secret, mapping, openemr_user_id)
        for mapping in mappings
        if mapping.zoom_account_id
    ]
    return jsonify({"streams": streams}), 200


@epic_bp.route("/screenpop/stream", methods=["GET"])
def screenpop_stream(zoom_account_id: str):
    # Flask passes zoom_account_id from the blueprint URL prefix; before_request
    # already resolved it onto g.zoom_account.
    _ = zoom_account_id
    account = g.zoom_account
    account_id = account.account_id
    openemr_user_id = str(request.args.get("openemr_user_id") or "").strip()
    if not openemr_user_id:
        return _stream_failure(account_id, None, "missing_openemr_user", status=400)

    secret = current_app.config.get("OPENEMR_FLASK_SECRET")
    if not secret:
        logger.error("epic.screenpop_stream | OPENEMR_FLASK_SECRET not configured")
        return _stream_failure(
            account_id,
            openemr_user_id,
            "missing_secret",
            status=500,
            error_message="missing secret",
        )

    try:
        expires_at = verify_screenpop_token(
            secret,
            account_id,
            openemr_user_id,
            request.args.get("expires"),
            request.args.get("token"),
        )
    except ScreenpopTokenError as e:
        return _stream_auth_error(account_id, openemr_user_id, e.reason, e.message)

    if not _has_active_agent_mapping(account_id, openemr_user_id):
        return _stream_failure(
            account_id,
            openemr_user_id,
            "mapping_not_active",
            status=403,
        )

    client_ip = _client_ip()
    q = subscribe(account_id, openemr_user_id)
    write_audit_log(
        event_type="epic_zcc.screenpop_subscribed",
        success=True,
        zoom_account_id=account_id,
        openemr_user_id=openemr_user_id,
        detail={
            "expires_at": expires_at,
            "client_ip": client_ip,
        },
    )

    app = current_app._get_current_object()
    cleanup_done = False

    def cleanup() -> None:
        nonlocal cleanup_done
        if cleanup_done:
            return
        cleanup_done = True
        unsubscribe(account_id, openemr_user_id, q)
        with app.app_context():
            write_audit_log(
                event_type="epic_zcc.screenpop_unsubscribed",
                success=True,
                zoom_account_id=account_id,
                openemr_user_id=openemr_user_id,
                detail={"client_ip": client_ip},
            )

    def generate():
        try:
            yield _sse_event("ping", {"ts": int(time.time())})
            while True:
                try:
                    event = q.get(timeout=_KEEPALIVE_SECONDS)
                except Empty:
                    yield _sse_event("ping", {"ts": int(time.time())})
                    continue
                event_name = str(event.get("type") or "message")
                yield _sse_event(event_name, event)
        except GeneratorExit:
            logger.debug(
                "epic.screenpop_stream | client disconnected "
                f"account_id={account_id} openemr_user_id={openemr_user_id}"
            )
        finally:
            cleanup()

    response = Response(
        generate(),
        status=200,
        content_type=_SSE_CONTENT_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    response.call_on_close(cleanup)
    return response


def _build_stream_descriptor(secret: str, mapping: UserMapping, openemr_user_id: str) -> dict:
    expires_at = int(time.time()) + EPIC_SCREENPOP_TOKEN_TTL_SECONDS
    token = make_screenpop_token(
        secret,
        mapping.zoom_account_id,
        openemr_user_id,
        expires_at,
    )
    openemr_base = (current_app.config.get("OPENEMR_PUBLIC_URL") or "").rstrip("/")
    query = urlencode({
        "account_id": mapping.zoom_account_id,
        "openemr_user_id": openemr_user_id,
        "expires": str(expires_at),
        "token": token,
    })
    return {
        "account_id": mapping.zoom_account_id,
        "url": f"{openemr_base}/interface/epic_cti/screenpop_stream.php?{query}",
        "expires_at": expires_at,
    }


def _active_agent_mappings_for_user(openemr_user_id: str) -> list[UserMapping]:
    return (
        UserMapping.query
        .join(ZoomAccount, UserMapping.zoom_account_id == ZoomAccount.account_id)
        .join(AccountConfig, AccountConfig.account_id == ZoomAccount.account_id)
        .filter(
            UserMapping.openemr_user_id == openemr_user_id,
            UserMapping.is_zcc_agent.is_(True),
            UserMapping.is_active.is_(True),
            UserMapping.zcc_user_id.isnot(None),
            UserMapping.zcc_user_id != "",
            ZoomAccount.is_active.is_(True),
            AccountConfig.epic_zcc_enabled.is_(True),
        )
        .order_by(UserMapping.zoom_account_id.asc())
        .all()
    )


def _has_active_agent_mapping(zoom_account_id: str, openemr_user_id: str) -> bool:
    return (
        UserMapping.query
        .join(ZoomAccount, UserMapping.zoom_account_id == ZoomAccount.account_id)
        .join(AccountConfig, AccountConfig.account_id == ZoomAccount.account_id)
        .filter(
            UserMapping.zoom_account_id == zoom_account_id,
            UserMapping.openemr_user_id == openemr_user_id,
            UserMapping.is_zcc_agent.is_(True),
            UserMapping.is_active.is_(True),
            UserMapping.zcc_user_id.isnot(None),
            UserMapping.zcc_user_id != "",
            ZoomAccount.is_active.is_(True),
            AccountConfig.epic_zcc_enabled.is_(True),
        )
        .first()
        is not None
    )


def _stream_failure(
    zoom_account_id: str | None,
    openemr_user_id: str | None,
    reason: str,
    *,
    status: int,
    error_message: str | None = None,
) -> Response:
    _audit_screenpop_failure(
        reason,
        zoom_account_id,
        openemr_user_id,
        error_message=error_message,
    )
    return Response(
        json.dumps({"error": reason}).encode("utf-8"),
        status=status,
        content_type=_JSON_CONTENT_TYPE,
    )


def _stream_auth_error(
    zoom_account_id: str | None,
    openemr_user_id: str | None,
    reason: str,
    error_message: str | None = None,
) -> Response:
    _audit_screenpop_failure(
        reason,
        zoom_account_id,
        openemr_user_id,
        error_message=error_message,
    )

    def generate():
        yield (
            f"retry: 86400000\n"
            f"event: auth_error\n"
            f"data: {json.dumps({'reason': reason})}\n\n"
        )

    return Response(
        generate(),
        status=200,
        content_type=_SSE_CONTENT_TYPE,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _audit_screenpop_failure(
    reason: str,
    zoom_account_id: str | None,
    openemr_user_id: str | None,
    *,
    error_message: str | None = None,
) -> None:
    write_audit_log(
        event_type="epic_zcc.screenpop_subscribe_failed",
        success=False,
        zoom_account_id=zoom_account_id,
        openemr_user_id=openemr_user_id,
        detail={"reason": reason, "client_ip": _client_ip()},
        error_message=error_message or reason,
    )


def _sse_event(event_name: str, data: dict) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    return f"event: {event_name}\ndata: {payload}\n\n"


def _client_ip() -> str | None:
    return (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
    )
