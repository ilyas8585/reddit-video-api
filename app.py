import os
import asyncio
import threading
import html

from flask import Flask, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

app = Flask(__name__)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

state = {
    "status": "idle",
    "qr_url": None,
    "session": None,
    "error": None
}


def telegram_login():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        client = TelegramClient(StringSession(), API_ID, API_HASH)

        try:
            await client.connect()

            qr = await client.qr_login()

            state["qr_url"] = qr.url
            state["status"] = "waiting"
            state["error"] = None

            try:
                await qr.wait(timeout=120)

            except SessionPasswordNeededError:
                state["status"] = "2fa_required"
                return

            state["session"] = client.session.save()
            state["status"] = "authorized"

        except asyncio.TimeoutError:
            state["status"] = "expired"

        except Exception as e:
            state["status"] = "error"
            state["error"] = f"{type(e).__name__}: {e}"

        finally:
            if client.is_connected():
                await client.disconnect()

    loop.run_until_complete(run())
    loop.close()


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "oibay-telegram"
    }


@app.get("/login")
def login():
    # создаём новый QR только если вход сейчас не выполняется
    if state["status"] not in ("waiting",):
        state["status"] = "starting"
        state["qr_url"] = None
        state["session"] = None
        state["error"] = None

        thread = threading.Thread(
            target=telegram_login,
            daemon=True
        )
        thread.start()

    page = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Oibay Telegram Login</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding-top: 40px;
        }

        #qr {
            width: 320px;
            height: 320px;
            margin: 20px auto;
        }

        #status {
            font-size: 20px;
            margin: 20px;
        }
    </style>
</head>

<body>

<h2>Oibay — Telegram Login</h2>

<div id="status">Создаю QR...</div>

<div id="qr"></div>

<p>
Telegram → Настройки → Устройства → Подключить устройство
</p>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>

<script>

let qrCreated = false;

async function check() {

    const response = await fetch("/login/status");
    const data = await response.json();

    const status = document.getElementById("status");

    if (data.status === "waiting") {

        status.innerText = "Отсканируй QR в Telegram";

        if (!qrCreated && data.qr_url) {

            new QRCode(
                document.getElementById("qr"),
                {
                    text: data.qr_url,
                    width: 320,
                    height: 320
                }
            );

            qrCreated = true;
        }
    }

    if (data.status === "authorized") {

        status.innerText = "✅ Telegram подключён";

        document.getElementById("qr").innerHTML = "";

        clearInterval(timer);
    }

    if (data.status === "expired") {

        status.innerText = "QR истёк. Обнови страницу.";

        clearInterval(timer);
    }

    if (data.status === "2fa_required") {

        status.innerText = "Требуется пароль двухэтапной проверки Telegram.";

        clearInterval(timer);
    }

    if (data.status === "error") {

        status.innerText = "Ошибка: " + data.error;

        clearInterval(timer);
    }
}

const timer = setInterval(check, 1000);

check();

</script>

</body>
</html>
"""

    return page


@app.get("/login/status")
def login_status():

    result = {
        "status": state["status"]
    }

    if state["status"] == "waiting":
        result["qr_url"] = state["qr_url"]

    if state["status"] == "error":
        result["error"] = state["error"]

    return jsonify(result)


@app.get("/session")
def get_session():

    if state["status"] != "authorized":
        return jsonify({
            "status": state["status"],
            "error": "Telegram not authorized"
        }), 400

    return jsonify({
        "status": "authorized",
        "session": state["session"]
    })
