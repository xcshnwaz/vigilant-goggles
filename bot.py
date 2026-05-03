import os
import logging
import subprocess
import requests
import sqlite3
import json
from flask import Flask, request as flask_request
from config import (
    TOKEN, BOT_DISPLAY_NAME, WEBHOOK_HOST, WEBHOOK_PORT, LOG_LEVEL
)
from db.database import init_db
from handlers.converter import handle_video, handle_v2mp3_callback
from handlers.core import (
    handle_start, handle_help, handle_unknown,
    delete_msg, send_message, edit_message, answer_callback
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Telegram API helper
# ---------------------------------------------------------------------------

def api(method: str, payload: dict = None, files=None, timeout: int = 30):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        if files:
            r = requests.post(url, data=payload or {}, files=files, timeout=timeout)
        else:
            r = requests.post(url, json=payload or {}, timeout=timeout)
        return r.json()
    except Exception as exc:
        log.error("API call %s failed: %s", method, exc)
        return {}


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True, silent=True) or {}
    log.debug("Update received: %s", json.dumps(data)[:300])

    # Callback query (inline button press)
    if "callback_query" in data:
        cq = data["callback_query"]
        cq_id   = cq.get("id")
        cq_data = cq.get("data", "")
        msg     = cq.get("message", {})
        chat_id = msg.get("chat", {}).get("id")

        answer_callback(api, cq_id)

        if cq_data.startswith("v2mp3:"):
            handle_v2mp3_callback(api, cq_data, chat_id)
        return "ok", 200

    # Regular message
    msg = data.get("message") or data.get("edited_message")
    if not msg:
        return "ok", 200

    chat_id = msg.get("chat", {}).get("id")
    msg_id  = msg.get("message_id")
    text    = (msg.get("text") or "").strip()

    if text.startswith("/start"):
        handle_start(api, chat_id, msg_id)
    elif text.startswith("/help"):
        handle_help(api, chat_id, msg_id)
    elif msg.get("video") or msg.get("document"):
        handle_video(api, msg, chat_id, msg_id)
    else:
        handle_unknown(api, chat_id, msg_id, text)

    return "ok", 200


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "bot": BOT_DISPLAY_NAME}, 200


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def set_webhook():
    url = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/{TOKEN}"
    log.info("Setting webhook -> %s", url)
    res = api("setWebhook", {"url": url, "drop_pending_updates": True})
    if res.get("ok"):
        log.info("Webhook set successfully.")
    else:
        log.warning("Webhook set failed: %s", res)


if __name__ == "__main__":
    init_db()
    set_webhook()
    app.run(host="0.0.0.0", port=int(WEBHOOK_PORT), debug=False)
