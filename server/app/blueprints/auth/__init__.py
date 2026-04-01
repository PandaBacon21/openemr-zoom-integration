from flask import Blueprint, current_app
from app.auth.jwks import build_jwks

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/")
def index():
    return {"blueprint": "auth", "status": "active"}


@auth_bp.route("/.well-known/jwks.json")
def jwks():
    """
    Public JWKS endpoint. OpenEMR fetches this to verify our JWT signatures.
    This URL gets registered with OpenEMR during app registration in Sprint 2.
    """
    key_path = current_app.config["JWKS_KEY_PATH"]
    return build_jwks(key_path)