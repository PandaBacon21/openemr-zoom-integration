import requests
from flask import request, Response
from app.blueprints.admin import admin_bp

DBGATE_BASE = "http://dbgate:3000"

@admin_bp.route("/db", defaults={"path": ""}, methods=["GET", "POST"])
@admin_bp.route("/db/<path:path>", methods=["GET", "POST"])
def proxy_dbgate(path):
    target_url = f"{DBGATE_BASE}/admin/db/{path}" if path else f"{DBGATE_BASE}/admin/db/"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    excluded_req = {"host", "content-length", "transfer-encoding"}
    headers = {k: v for k, v in request.headers if k.lower() not in excluded_req}

    # SSE streams must not be buffered
    is_stream = path == "stream" or "text/event-stream" in request.headers.get("Accept", "")

    resp = requests.request(
        method=request.method,
        url=target_url,
        headers=headers,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
        timeout=30,
        stream=is_stream,
    )

    content_type = resp.headers.get("Content-Type", "")

    if is_stream:
        def generate():
            for chunk in resp.iter_content(chunk_size=1):
                yield chunk
        return Response(
            generate(),
            status=resp.status_code,
            content_type=content_type,
            headers={"X-Accel-Buffering": "no"},
        )

    if "text/html" in content_type:
        body = resp.text
        body = body.replace('<head>', '<head><base href="/admin/db/">', 1)
        response_body = body.encode("utf-8")
    else:
        response_body = resp.content

    excluded_resp = {
        "content-encoding", "content-length", "transfer-encoding",
        "connection", "x-frame-options", "content-security-policy",
        "x-content-type-options",
    }
    response_headers = [
        (k, v) for k, v in resp.headers.items()
        if k.lower() not in excluded_resp
    ]

    return Response(
        response_body,
        status=resp.status_code,
        headers=response_headers,
        content_type=content_type,
    )