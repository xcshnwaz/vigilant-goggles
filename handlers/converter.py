import os
import subprocess
import logging
import requests

from config import (
    TOKEN, BOT_DISPLAY_NAME,
    MAX_FILE_BYTES, FFMPEG_TIMEOUT, AUDIO_BITRATE, AUDIO_SAMPLERATE
)
from handlers.core import send_message, edit_message, delete_msg, md
from db.database import (
    upsert_user, log_conversion, finish_conversion, increment_conversions
)

log = logging.getLogger("converter")

# In-memory store: "{chat_id}:{msg_id}" -> file_id
# (callback_data has a 64-byte limit so we cannot embed the full file_id)
_store: dict[str, str] = {}

# Unicode markers (small, clean, no emoji)
_ARROW   = "\u25b6"   # play triangle
_BULLET  = "\u2022"
_CHECK   = "\u2713"
_CROSS   = "\u2717"
_AUDIO   = "\u266a"   # musical note
_SPINNER = "\u29d7"   # hourglass-like


# ---------------------------------------------------------------------------
# Public handlers called from bot.py
# ---------------------------------------------------------------------------

def handle_video(api, msg: dict, chat_id: int, msg_id: int):
    """Called when a video or document message arrives."""
    video = msg.get("video") or msg.get("document")
    if not video:
        return

    file_id   = video.get("file_id", "")
    file_size = video.get("file_size", 0)

    # Size guard
    if file_size and file_size > MAX_FILE_BYTES:
        size_mb = MAX_FILE_BYTES // (1024 * 1024)
        send_message(
            api, chat_id,
            f"{_CROSS} File too large\\. Maximum allowed size is *{md(size_mb)} MB*\\.",
            reply_to=msg_id,
        )
        return

    if not file_id:
        return

    # Track user
    from_user = msg.get("from", {})
    upsert_user(
        chat_id,
        username=from_user.get("username"),
        first_name=from_user.get("first_name"),
    )

    # Store file_id keyed by chat:msg
    store_key = f"{chat_id}:{msg_id}"
    _store[store_key] = file_id

    title = (
        msg.get("caption")
        or video.get("file_name")
        or "Video"
    )[:40]

    buttons = [[
        {
            "text": f"{_AUDIO} Convert to MP3",
            "callback_data": f"v2mp3:{chat_id}:{msg_id}",
        }
    ]]

    send_message(
        api, chat_id,
        f"{_ARROW} *{md(title)}*\n\nTap the button below to extract audio as MP3\\.",
        reply_to=msg_id,
        buttons=buttons,
    )


def handle_v2mp3_callback(api, cq_data: str, chat_id: int):
    """Called when the 'Convert to MP3' inline button is pressed."""
    # cq_data format: "v2mp3:{orig_chat_id}:{orig_msg_id}"
    parts = cq_data.split(":")
    if len(parts) != 3:
        return
    _, orig_chat, orig_msg = parts
    store_key = f"{orig_chat}:{orig_msg}"

    file_id = _store.get(store_key)
    if not file_id:
        send_message(api, chat_id, f"{_CROSS} Session expired\\. Please resend the video\\.")
        return

    _convert_and_send(api, file_id, chat_id, int(orig_msg))


# ---------------------------------------------------------------------------
# Core conversion logic
# ---------------------------------------------------------------------------

def _convert_and_send(api, file_id: str, chat_id: int, reply_msg_id: int):
    uid      = f"{chat_id}_{reply_msg_id}"
    tmp_video = f"/tmp/v2a_{uid}_in"
    tmp_mp3   = f"/tmp/v2a_{uid}_out.mp3"
    status_id = None
    db_row_id = None

    try:
        # Status message
        sm = send_message(
            api, chat_id,
            f"{_SPINNER} Converting\\.\\.\\.",
            reply_to=reply_msg_id,
        )
        status_id = sm.get("result", {}).get("message_id")

        # Log to DB
        db_row_id = log_conversion(chat_id, reply_msg_id, file_id)

        # Resolve file path via Telegram
        fr = api("getFile", {"file_id": file_id})
        fp = fr.get("result", {}).get("file_path")
        if not fp:
            raise RuntimeError("Could not resolve file path from Telegram.")

        # Download
        ext = fp.rsplit(".", 1)[-1] if "." in fp else "mp4"
        tmp_video += f".{ext}"

        edit_message(api, chat_id, status_id, f"{_SPINNER} Downloading\\.\\.\\.")
        raw = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{fp}",
            timeout=120,
        ).content
        with open(tmp_video, "wb") as fh:
            fh.write(raw)

        # Convert with ffmpeg
        edit_message(api, chat_id, status_id, f"{_SPINNER} Extracting audio\\.\\.\\.")
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", tmp_video,
                "-vn",
                "-ar", str(AUDIO_SAMPLERATE),
                "-ac", "2",
                "-b:a", AUDIO_BITRATE,
                tmp_mp3,
            ],
            capture_output=True,
            timeout=FFMPEG_TIMEOUT,
        )

        if result.returncode != 0 or not os.path.exists(tmp_mp3):
            err = result.stderr.decode(errors="ignore")[-300:]
            log.error("ffmpeg error for %s: %s", uid, err)
            raise RuntimeError(f"ffmpeg exited with code {result.returncode}.")

        # Upload MP3
        edit_message(api, chat_id, status_id, f"{_SPINNER} Uploading\\.\\.\\.")
        with open(tmp_mp3, "rb") as fh:
            r = api(
                "sendAudio",
                {
                    "chat_id": chat_id,
                    "reply_to_message_id": reply_msg_id,
                    "title": "Audio",
                    "performer": BOT_DISPLAY_NAME,
                    "caption": f"{_CHECK} Conversion complete",
                    "parse_mode": "MarkdownV2",
                },
                files={"audio": fh},
                timeout=180,
            )

        if not r.get("ok"):
            raise RuntimeError(f"Upload failed: {r.get('description', 'unknown')}")

        finish_conversion(db_row_id, "done")
        increment_conversions(chat_id)
        log.info("Conversion done: chat=%s msg=%s", chat_id, reply_msg_id)

    except Exception as exc:
        log.exception("Conversion error: %s", exc)
        if db_row_id:
            finish_conversion(db_row_id, "error")
        short = str(exc)[:120]
        send_message(
            api, chat_id,
            f"{_CROSS} Conversion failed\\.\n_{md(short)}_",
            reply_to=reply_msg_id,
        )
    finally:
        delete_msg(api, chat_id, status_id)
        for path in [tmp_video, tmp_mp3]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
