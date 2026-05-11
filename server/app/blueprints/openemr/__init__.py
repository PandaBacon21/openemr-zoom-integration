from flask import Blueprint
from app.blueprints.auth.auth_helpers import verify_jwt_cookie_or_header


openemr_bp = Blueprint("openemr", __name__, url_prefix="/openemr")

@openemr_bp.before_request
def protect():
    return verify_jwt_cookie_or_header()


@openemr_bp.route("/")
def index():
    return {"blueprint": "openemr_routes", "status": "ok"}


from app.blueprints.openemr import openemr_routes