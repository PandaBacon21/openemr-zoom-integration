from flask import Blueprint, jsonify, request
from app.auth.api_key import protect_with_api_key
from app.models import ZoomAccount
from app.services.zoom import get_zoom_users

zoom_bp = Blueprint("zoom", __name__, url_prefix="/zoom")

@zoom_bp.before_request
def protect():
    return protect_with_api_key()

@zoom_bp.route("/users", methods=["GET"])
def get_users():

    zoom_account_id = request.args.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id query parameter is required"}), 400

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        return jsonify({"error": f"No active registration found for account {zoom_account_id}"}), 404

    search = request.args.get("search")

    try:
        users = get_zoom_users(account, search=search)
        return jsonify({
            "count": len(users),
            "users": users
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500