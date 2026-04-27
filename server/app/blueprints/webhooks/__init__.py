from flask import Blueprint


webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")


@webhooks_bp.route("/")
def index():
    return {"blueprint": "webhooks", "status": "ok"}


from app.blueprints.webhooks.openemr import openemr_webhook
from app.blueprints.webhooks.zoom import zoom_webhook