from flask import Blueprint
from app.blueprints.auth.auth_helpers import verify_jwt_request

audit_bp = Blueprint("audit", __name__, url_prefix="/audit")

@audit_bp.before_request
def protect():
    return verify_jwt_request()

from app.blueprints.audit import audit_routes