import logging

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import ZoomAccount
from app.services.registration import register_zoom_account, deregister_zoom_account

logger = logging.getLogger(__name__)

config_bp = Blueprint("config", __name__, url_prefix="/config")


@config_bp.route("/")
def index():
    return {"blueprint": "config", "status": "active"}


@config_bp.route("/register", methods=["POST"])
def register():
    """
    Register a Zoom account with the integration.

    Validates Zoom credentials, generates a keypair, registers with OpenEMR,
    and stores everything in the DB.

    Request body (JSON):
    {
        "zoom_account_id":     "abc123",
        "zoom_client_id":      "xyz...",
        "zoom_client_secret":  "secret...",
        "zoom_webhook_secret": "webhook_secret...",
        "contact_email":       "admin@example.com"
    }

    Responses:
        201 — registration successful, returns account summary
        400 — missing fields or validation error (bad credentials, duplicate)
        500 — unexpected server error
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields
    required = [
        "zoom_account_id",
        "zoom_client_id",
        "zoom_client_secret",
        "zoom_webhook_secret",
        "contact_email"
    ]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    try:
        account = register_zoom_account(
            zoom_account_id=data["zoom_account_id"],
            zoom_client_id=data["zoom_client_id"],
            zoom_client_secret=data["zoom_client_secret"],
            zoom_webhook_secret=data["zoom_webhook_secret"],
            contact_email=data["contact_email"],
        )

        return jsonify({
            "status": "registered",
            "zoom_account_id": account.account_id,
            "openemr_client_id": account.openemr_client_id,
            "kid": account.kid,
            "created_at": account.created_at.isoformat(),
        }), 201

    except ValueError as e:
        # Known validation errors — bad credentials, duplicate registration
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Registration failed for {data.get('zoom_account_id')}: {e}")
        return jsonify({"error": "Registration failed", "detail": str(e)}), 500


@config_bp.route("/register/<zoom_account_id>", methods=["DELETE"])
def deregister(zoom_account_id: str):
    """
    Deregister a Zoom account from the integration.

    Deregisters from OpenEMR, deletes the keypair, and removes the DB record.

    Responses:
        200 — deregistration successful
        404 — account not found
        500 — unexpected server error
    """
    try:
        deregister_zoom_account(zoom_account_id)
        return jsonify({
            "status": "deregistered",
            "zoom_account_id": zoom_account_id
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    except Exception as e:
        logger.error(f"Deregistration failed for {zoom_account_id}: {e}")
        return jsonify({"error": "Deregistration failed", "detail": str(e)}), 500


@config_bp.route("/registrations", methods=["GET"])
def list_registrations():
    """
    List all registered Zoom accounts and their status.

    Returns a summary of each registration — no secrets are included
    in the response, only identifiers and status fields.

    Responses:
        200 — list of registrations (may be empty)
    """
    accounts = ZoomAccount.query.order_by(ZoomAccount.created_at.desc()).all()

    return jsonify({
        "count": len(accounts),
        "registrations": [
            {
                "zoom_account_id": a.account_id,
                "openemr_client_id": a.openemr_client_id,
                "kid": a.kid,
                "is_active": a.is_active,
                "has_zoom_token": bool(a.zoom_access_token),
                "has_openemr_token": bool(a.openemr_access_token),
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
            }
            for a in accounts
        ]
    }), 200