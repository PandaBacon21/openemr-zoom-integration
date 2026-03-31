from flask import Blueprint

zoom_bp = Blueprint("zoom", __name__, url_prefix="/zoom")

@zoom_bp.route("/")
def index():
    return {"blueprint": "zoom", "status": "stub"}