from flask import Blueprint
from app.auth.api_key import protect_with_api_key


openemr_bp = Blueprint("openemr", __name__, url_prefix="/openemr")

@openemr_bp.before_request
def protect():
    return protect_with_api_key()


@openemr_bp.route("/")
def index():
    return {"blueprint": "openemr_routes", "status": "ok"}


from app.blueprints.openemr import openemr_routes