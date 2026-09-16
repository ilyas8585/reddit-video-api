import os
import asyncio

from flask import Flask, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
TG_SESSION = os.environ["TG_SESSION"]

SOURCE_CHANNEL = "davay_esche"


def run_async(coro):
    return asyncio.run(coro)


def make_client():
    return TelegramClient(
        StringSession(TG_SESSION),
        API_ID,
        API_HASH
    )


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "oibay-telegram"
    }


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

            async for message in client.iter_messages(entity, limit=30):

                if not message.video:
                    continue

                videos.append({
                    "message_id": message.id,
                    "date": message.date.isoformat(),
                    "caption": message.message or "",
                    "views": message.views or 0,
                    "duration": getattr(message.video, "duration", None),
                    "size": getattr(message.video, "size", None),
                    "link": f"https://t.me/{SOURCE_CHANNEL}/{message.id}"
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
        return jsonify(run_async(get_videos()))

    except Exception as e:
        return jsonify({
            "status": "error",
            "type": type(e).__name__,
            "error": str(e)
        }), 500
from flask import Response


@app.get("/telegram/video/<int:message_id>")
def telegram_video(message_id):

    async def download_video():
        client = make_client()
        await client.connect()

        try:
            message = await client.get_messages(
                SOURCE_CHANNEL,
                ids=message_id
            )

            if not message or not message.video:
                return None, None

            data = await client.download_media(
                message,
                file=bytes
            )

            filename = f"telegram_{message_id}.mp4"

            return data, filename

        finally:
            await client.disconnect()

    try:
        data, filename = run_async(download_video())

        if not data:
            return jsonify({
                "status": "error",
                "error": "Video not found"
            }), 404

        return Response(
            data,
            mimetype="video/mp4",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        return jsonify({
            "status": "error",
            "type": type(e).__name__,
            "error": str(e)
        }), 500
