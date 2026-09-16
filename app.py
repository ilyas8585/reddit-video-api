import os
import asyncio
import tempfile

from flask import Flask, jsonify, send_file, after_this_request
from telethon import TelegramClient
from telethon.sessions import StringSession


app = Flask(__name__)


# =========================
# CONFIG
# =========================

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
TG_SESSION = os.environ["TG_SESSION"]

SOURCE_CHANNEL = "davay_esche"


# =========================
# TELEGRAM
# =========================

def run_async(coro):
    return asyncio.run(coro)


def make_client():
    return TelegramClient(
        StringSession(TG_SESSION),
        API_ID,
        API_HASH
    )


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "oibay-telegram"
    }


# =========================
# TELEGRAM TEST
# =========================

@app.get("/telegram/test")
def telegram_test():

    async def test():
        client = make_client()
        await client.connect()

        try:
            authorized = await client.is_user_authorized()

            return {
                "status": "ok",
                "authorized": authorized
            }

        finally:
            await client.disconnect()

    try:
        return jsonify(run_async(test()))

    except Exception as e:
        return jsonify({
            "status": "error",
            "type": type(e).__name__,
            "error": str(e)
        }), 500


# =========================
# GET RECENT VIDEOS
# =========================

@app.get("/telegram/videos")
def telegram_videos():

    async def get_videos():

        client = make_client()
        await client.connect()

        try:
            if not await client.is_user_authorized():
                return {
                    "status": "error",
                    "error": "Telegram session is not authorized"
                }

            entity = await client.get_entity(SOURCE_CHANNEL)

            videos = []

            async for message in client.iter_messages(
                entity,
                limit=30
            ):

                if not message.video:
                    continue

                videos.append({
                    "message_id": message.id,
                    "date": message.date.isoformat(),
                    "caption": message.message or "",
                    "views": message.views or 0,
                    "duration": getattr(
                        message.video,
                        "duration",
                        None
                    ),
                    "size": getattr(
                        message.video,
                        "size",
                        None
                    ),
                    "link": (
                        f"https://t.me/"
                        f"{SOURCE_CHANNEL}/"
                        f"{message.id}"
                    )
                })

                if len(videos) >= 10:
                    break

            return {
                "status": "ok",
                "channel": SOURCE_CHANNEL,
                "count": len(videos),
                "videos": videos
            }

        finally:
            await client.disconnect()

    try:
        return jsonify(
            run_async(get_videos())
        )

    except Exception as e:
        return jsonify({
            "status": "error",
            "type": type(e).__name__,
            "error": str(e)
        }), 500


# =========================
# DOWNLOAD VIDEO
# =========================

@app.get("/telegram/video/<int:message_id>")
def telegram_video(message_id):

    async def download_video():

        client = make_client()
        await client.connect()

        try:
            if not await client.is_user_authorized():
                return None

            message = await client.get_messages(
                SOURCE_CHANNEL,
                ids=message_id
            )

            if not message or not message.video:
                return None

            filepath = os.path.join(
                tempfile.gettempdir(),
                f"telegram_{message_id}.mp4"
            )

            # ВАЖНО:
            # скачиваем видео на диск,
            # а не целиком в оперативную память.
            await client.download_media(
                message,
                file=filepath
            )

            return filepath

        finally:
            await client.disconnect()

    try:
        filepath = run_async(
            download_video()
        )

        if not filepath or not os.path.exists(filepath):
            return jsonify({
                "status": "error",
                "error": "Video not found"
            }), 404

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass

            return response

        return send_file(
            filepath,
            mimetype="video/mp4",
            as_attachment=True,
            download_name=f"telegram_{message_id}.mp4"
        )

    except Exception as e:
        return jsonify({
            "status": "error",
            "type": type(e).__name__,
            "error": str(e)
        }), 500
