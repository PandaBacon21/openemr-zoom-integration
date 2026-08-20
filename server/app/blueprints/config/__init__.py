from flask import Blueprint
from app.blueprints.auth.auth_helpers import verify_jwt_cookie_or_header


config_bp = Blueprint("config", __name__, url_prefix="/config")


@config_bp.before_request
def protect():
    return verify_jwt_cookie_or_header()


from app.blueprints.config import config_routes  # noqa: F401
from app.blueprints.config import demo_routes  # noqa: F401