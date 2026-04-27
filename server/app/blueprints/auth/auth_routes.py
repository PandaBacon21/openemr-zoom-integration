import jwt
import datetime
from flask import request, jsonify, current_app
from app.blueprints.auth import auth_bp


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    password = data.get("password", "")

    expected: str | None = current_app.config.get("CONFIG_ADMIN_PASSWORD")
    secret: str | None = current_app.config.get("CONFIG_JWT_SECRET")

    if not expected or not secret:
        return jsonify({"error": "Auth not configured on server"}), 500

    if password != expected:
        return jsonify({"error": "Invalid password"}), 401

    token = jwt.encode(
        {
            "sub": "admin",
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12),
        },
        secret,
        algorithm="HS256",
    )

    return jsonify({"token": token}), 200


@auth_bp.route("/verify", methods=["GET"])
def verify():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing token"}), 401

    token: str = auth_header.split(" ", 1)[1]
    secret: str | None = current_app.config.get("CONFIG_JWT_SECRET")

    if not secret: 
        return jsonify({"error": "Auth not configured on server"}), 500
    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return jsonify({"ok": True}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401