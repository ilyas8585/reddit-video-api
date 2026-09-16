import os
from flask import Flask, jsonify
from telethon import TelegramClient

app = Flask(__name__)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "oibay-telegram"
    }

@app.get("/test")
def test():
    return jsonify({
        "status": "ok",
        "telegram_configured": bool(API_ID and API_HASH)
    })
