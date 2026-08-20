import logging

from flask import current_app, g, jsonify, make_response, redirect, request

from app.models import UserMapping, ZoomAccount
from app.blueprints.veradigm import veradigm_bp
from app.blueprints.veradigm.veradigm_auth import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    mint_session_token,
    verify_launch_signature,
)
from app.blueprints.zoom.zoom_route_helper import verify_openemr_signature
from app.services.veradigm import (
    build_appointments_response,
    get_or_create_veradigm_meeting,
    provider_mappings_for_account,
)

logger = logging.getLogger(__name__)

_STANDALONE_PAGE = "/healthcare/veradigm/appointments"


def _active_account(account_id: str) -> ZoomAccount | None:
    return ZoomAccount.query.filter_by(account_id=account_id, is_active=True).first()


def _openemr_login_url() -> str:
    return current_app.config.get("OPENEMR_PUBLIC_URL") or "/"


# ---------------------------------------------------------------------------
# EHR launch — verify signed URL, set session cookie, redirect to the SPA page
# ---------------------------------------------------------------------------

@veradigm_bp.route("/launch", methods=["GET"])
def launch():
    u = request.args.get("u")
    ts = request.args.get("ts")
    sig = request.args.get("sig")

    if not verify_launch_signature(u, ts, sig):
        logger.warning("veradigm.launch | invalid/expired signature — bouncing to EHR login")
        return redirect(_openemr_login_url(), code=302)

    mapping = UserMapping.query.filter_by(
        openemr_user_id=str(u), is_provider=True, is_active=True
    ).first()
    if not mapping:
        logger.warning(f"veradigm.launch | openemr_user_id={u} has no provider mapping")
        return redirect(_openemr_login_url(), code=302)

    token = mint_session_token(provider_id=str(u), account_id=mapping.zoom_account_id)
    resp = make_response(redirect(_STANDALONE_PAGE, code=302))
    resp.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )
    return resp


@veradigm_bp.route("/ehr-login", methods=["GET"])
def ehr_login():
    """Bounce an unauthenticated standalone-page visitor back to the EHR login."""
    return redirect(_openemr_login_url(), code=302)


# ---------------------------------------------------------------------------
# Appointment list — dual context (EHR provider-scoped / admin account-scoped)
# ---------------------------------------------------------------------------

@veradigm_bp.route("/appointments", methods=["GET"])
def appointments():
    ctx = g.veradigm_ctx

    if ctx["context"] == "ehr":
        account = _active_account(ctx["account_id"])
        if not account:
            return jsonify({"error": "account_not_found"}), 404
        # Load every Veradigm provider's appointments; the page defaults to the
        # launching provider but lets them search/select colleagues.
        default_provider_id = str(ctx["provider_id"])
    else:  # admin
        account_id = request.args.get("zoom_account_id")
        if not account_id:
            return jsonify({"error": "zoom_account_id query parameter is required"}), 400
        account = _active_account(account_id)
        if not account:
            return jsonify({"error": "account_not_found"}), 404
        default_provider_id = None  # admin defaults to all providers

    mappings = provider_mappings_for_account(account.account_id)
    data = build_appointments_response(
        account.account_id, mappings, default_provider_id=default_provider_id
    )
    return jsonify(data), 200


# ---------------------------------------------------------------------------
# Start/Join — mint-or-reuse a Zoom meeting for a Veradigm appointment
# ---------------------------------------------------------------------------

_MEETING_ERROR_STATUS = {
    "appointment_not_found": 404,
    "not_veradigm_appointment": 400,
    "provider_not_mapped": 409,
    "zoom_create_failed": 502,
}


@veradigm_bp.route("/appointments/<string:eid>/meeting", methods=["POST"])
def create_meeting(eid: str):
    ctx = g.veradigm_ctx

    if ctx["context"] == "ehr":
        account = _active_account(ctx["account_id"])
    else:  # admin
        body = request.get_json(silent=True) or {}
        account_id = request.args.get("zoom_account_id") or body.get("zoom_account_id")
        if not account_id:
            return jsonify({"error": "zoom_account_id is required"}), 400
        account = _active_account(account_id)

    if not account:
        return jsonify({"error": "account_not_found"}), 404

    result = get_or_create_veradigm_meeting(account, eid)
    if "error" in result:
        return jsonify(result), _MEETING_ERROR_STATUS.get(result["error"], 500)
    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Nav-icon bootstrap — HMAC body-signed; tells OpenEMR whether to show the icon
# ---------------------------------------------------------------------------

@veradigm_bp.route("/nav-bootstrap", methods=["POST"])
@verify_openemr_signature
def nav_bootstrap():
    body = request.get_json(silent=True) or {}
    openemr_user_id = body.get("openemr_user_id")
    if not openemr_user_id:
        return jsonify({"error": "openemr_user_id is required"}), 400

    mapping = UserMapping.query.filter_by(
        openemr_user_id=str(openemr_user_id), is_provider=True, is_active=True
    ).first()

    return jsonify({
        "is_provider": mapping is not None,
        "provider_id": str(openemr_user_id) if mapping else None,
        "account_id": mapping.zoom_account_id if mapping else None,
    }), 200
