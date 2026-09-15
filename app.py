import requests
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "reddit-video-api",
        "mode": "reddit-debug"
    }


@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = data.get("url")

    if not url:
        return jsonify({"error": "url is required"}), 400

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(
            url,
            headers=headers,
            allow_redirects=True,
            timeout=20
        )

        content_type = r.headers.get("content-type", "")

        if "text" in content_type or "json" in content_type:
            body_preview = r.text[:500]
        else:
            body_preview = "[binary response]"

        return jsonify({
            "input_url": url,
            "status_code": r.status_code,
            "final_url": r.url,
            "content_type": content_type,
            "content_length": r.headers.get("content-length"),
            "body_preview": body_preview
        })

    except BaseException as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__,
            "input_url": url
        }), 500
