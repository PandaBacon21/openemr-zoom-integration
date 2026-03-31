from flask import Blueprint

config_bp = Blueprint("config", __name__, url_prefix="/config")

@config_bp.route("/")
def index():
    return {"blueprint": "config", "status": "stub"}