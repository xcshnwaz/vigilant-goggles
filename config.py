import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Required
# ---------------------------------------------------------------------------
TOKEN           = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
BOT_DISPLAY_NAME = os.getenv("BOT_NAME", "AudioBot")

# ---------------------------------------------------------------------------
# Render / hosting
# ---------------------------------------------------------------------------
WEBHOOK_HOST    = os.getenv("RENDER_EXTERNAL_HOSTNAME", "your-service.onrender.com")
WEBHOOK_PORT    = os.getenv("PORT", "10000")

# ---------------------------------------------------------------------------
# Database — MongoDB
# ---------------------------------------------------------------------------
MONGO_URI       = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME   = os.getenv("MONGO_DB_NAME", "audiobot")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------
MAX_FILE_BYTES  = int(os.getenv("MAX_FILE_BYTES", str(50 * 1024 * 1024)))   # 50 MB
FFMPEG_TIMEOUT  = int(os.getenv("FFMPEG_TIMEOUT", "180"))
AUDIO_BITRATE   = os.getenv("AUDIO_BITRATE", "192k")
AUDIO_SAMPLERATE = int(os.getenv("AUDIO_SAMPLERATE", "44100"))
