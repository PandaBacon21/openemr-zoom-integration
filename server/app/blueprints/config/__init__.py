from flask import Blueprint
from app.auth.api_key import protect_with_api_key


config_bp = Blueprint("config", __name__, url_prefix="/config")


@config_bp.before_request
def protect():
    return protect_with_api_key()


@config_bp.route("/")
def index():
    return {"blueprint": "config_routes", "status": "active"}


from app.blueprints.config import config_routes 