import jwt
from flask import current_app, g, jsonify, request

from app.services.audit import write_audit_log
from app.services.epic.token_store import validate_token


def verify_jwt_cookie_or_header() -> None | tuple:
    token = request.cookies.get("admin_token")

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]

    secret: str | None = current_app.config.get("CONFIG_JWT_SECRET")
    if not secret:
        return jsonify({"error": "JWT secret not configured"}), 500

    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return None
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception:
        return jsonify({"error": "Auth error"}), 401


def verify_bearer_token_in_store() -> None | tuple:
    """Resolve an Epic-ZCC opaque bearer token to its Zoomly account.

    Used by the Epic-shaped data endpoints (PatientLookUp, Practitioner,
    ReceiveCommunication3). Token is minted by `/oauth2/token` and lives
    in `app.services.epic.token_store`.

    On success the resolved zoom_account_id is cross-checked against the
    path's `zoom_account_id` view arg (defense-in-depth: a token issued
    to account A must not work on account B's endpoints) and attached to
    `flask.g.bearer_zoom_account_id`. Returns None on success, a (jsonify,
    status) tuple on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        write_audit_log(
            event_type="epic_zcc.bearer_token_invalid",
            success=False,
            detail={"reason": "missing_header"},
        )
        return jsonify({"error": "invalid_token", "error_description": "missing bearer"}), 401

    token = auth_header.split(" ", 1)[1]
    account_id = validate_token(token)
    if not account_id:
        write_audit_log(
            event_type="epic_zcc.bearer_token_invalid",
            success=False,
            detail={"reason": "expired_or_unknown"},
        )
        return jsonify({"error": "invalid_token", "error_description": "expired or unknown"}), 401

    path_account_id = request.view_args.get("zoom_account_id") if request.view_args else None
    if path_account_id and path_account_id != account_id:
        write_audit_log(
            event_type="epic_zcc.bearer_token_invalid",
            success=False,
            zoom_account_id=account_id,
            detail={"reason": "account_mismatch", "path_account_id": path_account_id},
        )
        return jsonify({"error": "invalid_token", "error_description": "account mismatch"}), 401

    g.bearer_zoom_account_id = account_id
    return None