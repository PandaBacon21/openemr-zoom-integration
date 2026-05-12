def verify_jwt_cookie_or_header() -> None | tuple:
    import jwt
    from flask import request, jsonify, current_app

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