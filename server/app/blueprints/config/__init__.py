from flask import Blueprint
from app.blueprints.auth.auth_helpers import verify_jwt_request


config_bp = Blueprint("config", __name__, url_prefix="/config")


@config_bp.before_request
def protect():
    return verify_jwt_request()


@config_bp.route("/")
def index():
    return {"blueprint": "config_routes", "status": "active"}


from app.blueprints.config import config_routes 