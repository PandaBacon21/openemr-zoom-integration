import functools
from flask import request, current_app
from werkzeug.exceptions import Unauthorized


def require_api_key(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != current_app.config["API_KEY"]:
            raise Unauthorized("Invalid or missing API key")
        return f(*args, **kwargs)
    return decorated

def protect_with_api_key():
    from flask import request, jsonify, current_app
    api_key = request.headers.get("X-API-Key")
    expected = current_app.config.get("API_KEY")
    if not expected:
        return jsonify({"error": "API_KEY not configured on server"}), 500
    if not api_key or api_key != expected:
        return jsonify({"error": "Invalid or missing API key"}), 401