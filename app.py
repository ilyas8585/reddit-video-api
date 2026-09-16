import os
import asyncio

from flask import Flask, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
TG_SESSION = os.environ["TG_SESSION"]


def run_async(coro):
    return asyncio.run(coro)


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "oibay-telegram"
    }


@app.get("/telegram/test")
def telegram_test():

    async def test():
        client = TelegramClient(
            StringSession(TG_SESSION),
            API_ID,
            API_HASH
        )

        await client.connect()

        try:
            authorized = await client.is_user_authorized()

            if not authorized:
                return {
                    "status": "error",
                    "authorized": False
                }

            me = await client.get_me()

            return {
                "status": "ok",
                "authorized": True,
                "user_id": me.id,
                "first_name": me.first_name
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
