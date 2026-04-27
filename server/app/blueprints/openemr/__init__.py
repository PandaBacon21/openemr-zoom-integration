from flask import Blueprint, jsonify, request
from app.auth.api_key import protect_with_api_key
from app.models import ZoomAccount
from app.services.openemr import get_practitioners, get_appointment_types_list

openemr_bp = Blueprint("openemr", __name__)

@openemr_bp.before_request
def protect():
    return protect_with_api_key()


@openemr_bp.route("/openemr/providers", methods=["GET"])
def get_providers():

    zoom_account_id = request.args.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id query parameter is required"}), 400

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        return jsonify({"error": f"No active registration found for account {zoom_account_id}"}), 404

    search = request.args.get("search")
    practitioner_id = request.args.get("id")

    try:
        practitioners = get_practitioners(account, search=search, practitioner_id=practitioner_id)
        return jsonify({
            "count": len(practitioners),
            "providers": practitioners
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@openemr_bp.route("/openemr/appointment-types", methods=["GET"])
def get_appointment_types():
    try:
        types = get_appointment_types_list()
        return jsonify({
            "count": len(types),
            "appointment_types": types
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500