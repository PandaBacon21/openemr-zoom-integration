from flask import Blueprint, request
from app.blueprints.auth.auth_helpers import verify_jwt_cookie_or_header


zoom_bp = Blueprint("zoom", __name__, url_prefix="/zoom")


@zoom_bp.before_request
def protect():
    if request.endpoint == "zoom.fetch_zoom_note" or request.endpoint == "zoom.complete_zoom_note":
        return
    return verify_jwt_cookie_or_header()


@zoom_bp.route("/")
def index():
    return {"blueprint": "zoom_routes", "status": "ok"}


from app.blueprints.zoom import zoom_routes 