import os
import glob
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

        # redvid expects the full v.redd.it URL
        reddit.url = url
        reddit.path = workdir + "/"

        result = reddit.download()

        # If redvid returns the path directly
        file_path = (
            result
            if isinstance(result, str) and os.path.exists(result)
            else None
        )

        # Otherwise find the resulting MP4 in the temp directory
        if not file_path:
            files = glob.glob(os.path.join(workdir, "*.mp4"))
            if files:
                file_path = max(files, key=os.path.getmtime)

        if not file_path:
            return jsonify({
                "error": "download finished but mp4 was not found"
            }), 500

        return send_file(
            file_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="reddit.mp4"
        )

    except BaseException as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__,
            "received_url": url
        }), 500
