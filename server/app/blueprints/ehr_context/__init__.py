from flask import Blueprint

ehr_context_bp = Blueprint("ehr", __name__, url_prefix="/rest")

from app.blueprints.ehr_context import ehr_context_routes 