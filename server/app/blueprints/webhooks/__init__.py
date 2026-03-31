from flask import Blueprint

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")

@webhooks_bp.route("/")
def index():
    return {"blueprint": "webhooks", "status": "stub"}