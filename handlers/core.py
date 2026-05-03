import logging
import re

log = logging.getLogger("core")

# ---------------------------------------------------------------------------
# Markdown escape (MarkdownV2)
# ---------------------------------------------------------------------------

_MD_SPECIAL = r"\_*[]()~`>#+-=|{}.!"

def md(text: str) -> str:
    """Escape text for Telegram MarkdownV2."""
    return re.sub(r"([" + re.escape(_MD_SPECIAL) + r"])", r"\\\1", str(text))


# ---------------------------------------------------------------------------
# Low-level send helpers
# ---------------------------------------------------------------------------

def send_message(api, chat_id: int, text: str, reply_to: int = None,
                 buttons: list = None, parse_mode: str = "MarkdownV2") -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return api("sendMessage", payload)


def edit_message(api, chat_id: int, msg_id: int, text: str,
                 parse_mode: str = "MarkdownV2") -> dict:
    return api("editMessageText", {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text,
        "parse_mode": parse_mode,
    })


def delete_msg(api, chat_id: int, msg_id: int | None):
    if msg_id:
        api("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})


def answer_callback(api, callback_id: str, text: str = ""):
    api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

def handle_start(api, chat_id: int, msg_id: int):
    text = (
        "*Welcome to AudioBot*\n"
        "\n"
        "Send or forward any video and I will extract the audio as an MP3 file\\.\n"
        "\n"
        "Commands\n"
        "/start  \\- Show this message\n"
        "/help   \\- How to use the bot\n"
    )
    buttons = [
        [
            {"text": "Help", "callback_data": "help"},
            {"text": "Source", "url": "https://github.com/yourrepo/audiobot"},
        ]
    ]
    send_message(api, chat_id, text, reply_to=msg_id, buttons=buttons)


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

def handle_help(api, chat_id: int, msg_id: int):
    text = (
        "*How to use AudioBot*\n"
        "\n"
        "1\\. Send a video file \\(MP4, MKV, AVI, etc\\.\\)\n"
        "2\\. Tap the *Convert to MP3* button that appears\n"
        "3\\. Receive your MP3 audio file\n"
        "\n"
        "*Limits*\n"
        "\\- Max file size: 50 MB\n"
        "\\- Audio: 192 kbps, 44100 Hz, stereo\n"
        "\n"
        "If conversion fails, make sure the file is a valid video\\."
    )
    send_message(api, chat_id, text, reply_to=msg_id)


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def handle_unknown(api, chat_id: int, msg_id: int, text: str):
    if not text:
        return
    send_message(
        api, chat_id,
        "Send a video file to convert it to MP3\\.\nType /help for instructions\\.",
        reply_to=msg_id,
    )
