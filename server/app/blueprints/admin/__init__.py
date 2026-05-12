from flask import Blueprint
from app.blueprints.auth.auth_helpers import verify_jwt_cookie_or_header

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.before_request
def protect():
    return verify_jwt_cookie_or_header()

from app.blueprints.admin import admin_routes  