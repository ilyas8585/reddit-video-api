import os
import asyncio
from flask import Flask, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

qr_state = {}


@app.get("/")
def home():
    return {"status": "ok", "service": "oibay-telegram"}


@app.get("/auth/qr")
def create_qr():
    async def run():
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()

        qr_login = await client.qr_login()

        qr_state["client"] = client
        qr_state["qr_login"] = qr_login

        return qr_login.url

    try:
        url = asyncio.run(run())

        return {
            "status": "qr_ready",
            "qr_url": url
        }

    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 400


@app.get("/auth/qr-check")
def qr_check():
    async def run():
        client = qr_state.get("client")
        qr_login = qr_state.get("qr_login")

        if not client or not qr_login:
            return {"status": "create_qr_first"}

        try:
            await qr_login.wait(timeout=5)

            session_string = client.session.save()
            await client.disconnect()

            return {
                "status": "authorized",
                "session": session_string
            }

        except asyncio.TimeoutError:
            return {"status": "waiting_for_scan"}

    try:
        return asyncio.run(run())

    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 400
