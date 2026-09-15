import os
import tempfile
from flask import Flask, request, send_file, jsonify
from redvid import Downloader

app = Flask(__name__)

@app.get("/")
def home():
    return {"status": "ok", "service": "reddit-video-api"}

@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = data.get("url")

    if not url:
        return jsonify({"error": "url is required"}), 400

    try:
        workdir = tempfile.mkdtemp()

        reddit = Downloader(max_q=True)
        reddit.url = url
        reddit.path = workdir

        file_path = reddit.download()

        if not file_path or not os.path.exists(file_path):
            return jsonify({"error": "download failed"}), 500

        return send_file(
            file_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="reddit.mp4"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
