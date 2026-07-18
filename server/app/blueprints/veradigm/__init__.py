from flask import Blueprint, g, jsonify, request

from app.blueprints.veradigm.veradigm_auth import resolve_context

veradigm_bp = Blueprint("veradigm", __name__, url_prefix="/veradigm")

# Endpoints that authenticate themselves (not via the dual-context guard):
#   veradigm.launch        — verifies the signed launch URL, then sets the cookie
#   veradigm.nav_bootstrap — HMAC body-signed (verify_openemr_signature)
#   veradigm.ehr_login     — public bounce back to the EHR login
_SELF_AUTHED = {"veradigm.launch", "veradigm.nav_bootstrap", "veradigm.ehr_login"}


@veradigm_bp.before_request
def protect():
    if request.endpoint in _SELF_AUTHED:
        return
    ctx = resolve_context()
    if ctx is None:
        return jsonify({"error": "unauthorized"}), 401
    g.veradigm_ctx = ctx


from app.blueprints.veradigm import veradigm_routes  # noqa: E402,F401
