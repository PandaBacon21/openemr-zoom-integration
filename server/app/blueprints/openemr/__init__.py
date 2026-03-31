from flask import Blueprint

openemr_bp = Blueprint("openemr", __name__, url_prefix="/openemr")

@openemr_bp.route("/")
def index():
    return {"blueprint": "openemr", "status": "stub"}