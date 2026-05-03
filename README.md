# AudioBot

A Telegram bot that extracts audio from video files and sends them as MP3.

---

## Features

- Send any video file (MP4, MKV, AVI, MOV, ...)
- Tap **Convert to MP3** inline button
- Receive a 192 kbps stereo MP3 instantly
- SQLite database logs every conversion
- One-click deploy to Render.com

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/yourrepo/audiobot.git
cd audiobot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Make sure `ffmpeg` is installed on your system:

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and set BOT_TOKEN at minimum
```

### 4. Run locally

```bash
python bot.py
```

For local testing use [ngrok](https://ngrok.com) to expose your port and set `RENDER_EXTERNAL_HOSTNAME` to your ngrok domain.

---

## Deploy to Render

1. Push the repo to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Connect your GitHub repo.
4. Set the environment variable `BOT_TOKEN` in the Render dashboard.
5. Render will auto-detect `render.yaml` and configure everything else.
6. After the first deploy the webhook URL is set automatically.

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | Yes | - | Telegram bot token |
| `BOT_NAME` | No | AudioBot | Performer name on MP3 |
| `RENDER_EXTERNAL_HOSTNAME` | Yes on Render | - | Auto-set by Render |
| `PORT` | Yes on Render | 10000 | Auto-set by Render |
| `DB_PATH` | No | data/bot.db | SQLite file path |
| `LOG_LEVEL` | No | INFO | DEBUG/INFO/WARNING/ERROR |
| `MAX_FILE_BYTES` | No | 52428800 | Max upload size (bytes) |
| `FFMPEG_TIMEOUT` | No | 180 | Seconds before ffmpeg kill |
| `AUDIO_BITRATE` | No | 192k | MP3 bitrate |
| `AUDIO_SAMPLERATE` | No | 44100 | Sample rate in Hz |

---

## Project Layout

```
audiobot/
  bot.py              # Flask app + webhook endpoint
  config.py           # All settings from env vars
  render.yaml         # Render.com deploy config
  Procfile            # gunicorn start command
  requirements.txt
  handlers/
    core.py           # /start, /help, send helpers
    converter.py      # Video -> MP3 logic
  db/
    database.py       # SQLite schema + helpers
  data/               # Created at runtime (gitignored)
```

---

## License

MIT
