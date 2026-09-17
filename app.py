import os
import asyncio
import tempfile

from flask import Flask, jsonify, send_file, request
from telethon import TelegramClient
from telethon.sessions import StringSession


app = Flask(__name__)


# =========================
# CONFIG
# =========================

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
TG_SESSION = os.environ["TG_SESSION"]

SOURCE_CHANNELS = [
    "prikoly_memy_yumorn",
    "fun_vidos",
    "faill_army",
    "zhabqua"
]

# =========================
# PUBLISHED VIDEOS
# =========================

PUBLISHED_FILE = "/tmp/oibay_published.txt"


def load_published():
    if not os.path.exists(PUBLISHED_FILE):
        return set()

    with open(PUBLISHED_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_published(key):
    with open(PUBLISHED_FILE, "a") as f:
        f.write(key + "\n")


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
        "service": "oibay-telegram",
        "channels": SOURCE_CHANNELS
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
            "error": str(e),
            "type": type(e).__name__
        }), 500


# =========================
# GET VIDEOS
# =========================

@app.get("/telegram/videos")
def telegram_videos():

    async def get_videos():

        client = make_client()
        await client.connect()

        result = []
        published = load_published()

        try:

            for channel_name in SOURCE_CHANNELS:

                try:
                    entity = await client.get_entity(channel_name)

                    # Берём последние сообщения с запасом,
                    # чтобы найти до 10 видео с каждого канала
                    async for message in client.iter_messages(
                        entity,
                        limit=50
                    ):

                        if not message.video:
                            continue
                            key = f"{channel_name}:{message.id}"

                            if key in published:
                                continue

                        result.append({
                            "channel": channel_name,
                            "message_id": message.id,
                            "caption": message.message or "",
                            "views": message.views or 0,
                            "date": (
                                message.date.isoformat()
                                if message.date
                                else None
                            ),

                            # Уникальная ссылка одновременно является
                            # хорошим ключом для Remove Duplicates в n8n
                            "link": (
                                f"https://t.me/"
                                f"{channel_name}/"
                                f"{message.id}"
                            ),

                            # Используем это поле для скачивания
                            "download_url": (
                                f"/telegram/video/"
                                f"{channel_name}/"
                                f"{message.id}"
                            )
                        })

                        # Максимум 10 видео с одного канала
                        channel_count = sum(
                            1 for item in result
                            if item["channel"] == channel_name
                        )

                        if channel_count >= 10:
                            break

                except Exception as channel_error:

                    # Ошибка одного канала не ломает остальные
                    result.append({
                        "channel": channel_name,
                        "error": str(channel_error)
                    })

            # Самые свежие ролики первыми
            valid_videos = [
                item for item in result
                if "message_id" in item
            ]

            valid_videos.sort(
                key=lambda x: x["date"] or "",
                reverse=True
            )

            return {
                "status": "ok",
                "channels": SOURCE_CHANNELS,
                "count": len(valid_videos),
                "videos": valid_videos
            }

        finally:
            await client.disconnect()

    try:
        return jsonify(run_async(get_videos()))

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "type": type(e).__name__
        }), 500


# =========================
# DOWNLOAD VIDEO
# =========================

@app.get("/telegram/video/<channel>/<int:message_id>")
def telegram_video(channel, message_id):

    # Разрешаем скачивание только
    # из каналов нашего списка
    if channel not in SOURCE_CHANNELS:
        return jsonify({
            "status": "error",
            "error": "Channel not allowed"
        }), 404

    async def download():

        client = make_client()
        await client.connect()

        try:
            entity = await client.get_entity(channel)

            message = await client.get_messages(
                entity,
                ids=message_id
            )

            if not message:
                raise Exception("Message not found")

            if not message.video:
                raise Exception("Message does not contain video")

            temp_dir = tempfile.gettempdir()

            file_path = os.path.join(
                temp_dir,
                f"telegram_{channel}_{message_id}.mp4"
            )

            downloaded = await client.download_media(
                message,
                file=file_path
            )

            if not downloaded:
                raise Exception("Video download failed")

            return downloaded

        finally:
            await client.disconnect()

    try:
        file_path = run_async(download())

        return send_file(
            file_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "type": type(e).__name__,
            "channel": channel,
            "message_id": message_id
        }), 500

@app.post("/telegram/published")
def telegram_published():
    data = request.get_json(silent=True) or {}

    channel = data.get("channel")
    message_id = data.get("message_id")

    if not channel or not message_id:
        return jsonify({
            "status": "error",
            "error": "channel and message_id required"
        }), 400

    key = f"{channel}:{message_id}"
    save_published(key)

    return jsonify({
        "status": "ok",
        "published": key
    })
@app.get("/telegram/frame/<channel>/<int:message_id>")
def telegram_frame(channel, message_id):
    import subprocess
    import imageio_ffmpeg

    async def make_frame():
        client = TelegramClient(
            StringSession(TG_SESSION),
            API_ID,
            API_HASH
        )

        await client.connect()

        try:
            message = await client.get_messages(channel, ids=message_id)

            if not message or not message.video:
                raise Exception("Video not found")

            video_path = f"/tmp/{channel}_{message_id}.mp4"
            frame_path = f"/tmp/{channel}_{message_id}.jpg"

            await client.download_media(message, file=video_path)

            frames = []

for i, sec in enumerate([2, 5, 8], start=1):
    frame = f"/tmp/{channel}_{message_id}_{i}.jpg"

    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-ss", str(sec),
        "-i", video_path,
        "-frames:v", "1",
        frame
    ], check=True)

    frames.append(frame)

            return frames

        finally:
            await client.disconnect()

    try:
        frames = run_async(make_frame())

        return jsonify({
    "status": "ok",
    "frames": [
        f"/telegram/frame-image/{channel}/{message_id}/1",
        f"/telegram/frame-image/{channel}/{message_id}/2",
        f"/telegram/frame-image/{channel}/{message_id}/3"
    ]
})

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
        @app.get("/telegram/frame-image/<channel>/<int:message_id>/<int:number>")
def telegram_frame_image(channel, message_id, number):
    if number not in [1, 2, 3]:
        return jsonify({"status": "error"}), 404

    frame_path = f"/tmp/{channel}_{message_id}_{number}.jpg"

    if not os.path.exists(frame_path):
        return jsonify({"status": "error", "error": "Frame not found"}), 404

    return send_file(frame_path, mimetype="image/jpeg")
# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
