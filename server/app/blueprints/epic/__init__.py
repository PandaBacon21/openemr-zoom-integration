"""Epic-style ZCC CTI middleware blueprint.

Mounted at `/zoomly/<zoom_account_id>/interconnect-amcurprd-oauth` so each
Zoomly account presents its own Epic Instance URL to Zoom Contact Center.

Account resolution happens in `before_request` and attaches the account to
`flask.g.zoom_account`. Per-route Bearer auth (for PatientLookUp /
Practitioner / ReceiveCommunication3) is applied inside each handler via
`verify_bearer_token_in_store()`; the token + JWKS bootstrap endpoints
intentionally stay public.
"""
import logging
from flask import Blueprint, g, jsonify, request

from app.models import ZoomAccount


logger = logging.getLogger(__name__)

epic_bp = Blueprint(
    "epic",
    __name__,
    url_prefix="/zoomly/<zoom_account_id>/interconnect-amcurprd-oauth",
)


@epic_bp.before_request
def resolve_account():
    """Look up the ZoomAccount from the path and gate on epic_zcc_enabled.

    External callers see 404 in both the "account doesn't exist" and the
    "CTI is disabled for this account" cases — Zoom shouldn't be able to
    distinguish those from probes.
    """

    zoom_account_id = request.view_args.get("zoom_account_id") if request.view_args else None
    if not zoom_account_id:
        return jsonify({"error": "not_found"}), 404

    account = ZoomAccount.query.filter_by(account_id=zoom_account_id, is_active=True).first()
    if not account:
        logger.info(f"epic | Unknown or inactive account in path: {zoom_account_id}")
        return jsonify({"error": "not_found"}), 404

    if not (account.config and account.config.epic_zcc_enabled):
        logger.info(f"epic | CTI not enabled for account {zoom_account_id}")
        return jsonify({"error": "not_found"}), 404

    g.zoom_account = account
    return None


from app.blueprints.epic import auth_routes 
from app.blueprints.epic import patient_routes  
from app.blueprints.epic import practitioner_routes
