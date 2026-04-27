from flask import request, current_app

def protect_with_api_key():
    from flask import request, jsonify, current_app
    api_key = request.headers.get("X-API-Key")
    expected = current_app.config.get("API_KEY")
    if not expected:
        return jsonify({"error": "API_KEY not configured on server"}), 500
    if not api_key or api_key != expected:
        return jsonify({"error": "Invalid or missing API key"}), 401