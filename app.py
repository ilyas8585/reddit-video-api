import os
import asyncio
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

pending = {}


@app.get("/")
def home():
    return {"status": "ok", "service": "oibay-telegram"}


@app.get("/test")
def test():
    return {
        "status": "ok",
        "telegram_configured": bool(API_ID and API_HASH)
    }


@app.post("/auth/send-code")
def send_code():
    phone = (request.get_json(silent=True) or {}).get("phone")

    if not phone:
        return jsonify({"error": "phone required"}), 400

    async def run():
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()

        sent = await client.send_code_request(phone)

        pending[phone] = {
            "session": client.session.save(),
            "phone_code_hash": sent.phone_code_hash
        }

        delivery_type = type(sent.type).__name__

        await client.disconnect()
        return delivery_type

    try:
        delivery_type = asyncio.run(run())

        return {
            "status": "code_sent",
            "delivery": delivery_type
        }

    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 400


@app.post("/auth/verify")
def verify():
    data = request.get_json(silent=True) or {}

    phone = data.get("phone")
    code = data.get("code")

    if phone not in pending:
        return jsonify({"error": "send code first"}), 400

    async def run():
        p = pending[phone]

        client = TelegramClient(
            StringSession(p["session"]),
            API_ID,
            API_HASH
        )

        await client.connect()

        await client.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=p["phone_code_hash"]
        )

        session_string = client.session.save()

        await client.disconnect()

        return session_string

    try:
        session_string = asyncio.run(run())

        return {
            "status": "authorized",
            "session": session_string
        }

    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 400
