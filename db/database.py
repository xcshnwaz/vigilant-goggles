"""
MongoDB helpers.

Collections
-----------
users       – one doc per chat_id, tracks usage stats
conversions – one doc per conversion job
"""

import logging
from datetime import datetime, timezone

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure

from config import MONGO_URI, MONGO_DB_NAME

log = logging.getLogger("db")

# ---------------------------------------------------------------------------
# Connection (module-level singleton)
# ---------------------------------------------------------------------------

_client: MongoClient | None = None


def _db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[MONGO_DB_NAME]


def init_db():
    """Verify connection and create indexes."""
    try:
        db = _db()
        db.command("ping")
        log.info("MongoDB connected: %s / %s", MONGO_URI.split("@")[-1], MONGO_DB_NAME)
    except ConnectionFailure as exc:
        log.error("MongoDB connection failed: %s", exc)
        raise

    # Indexes
    db.users.create_index([("chat_id", ASCENDING)], unique=True)
    db.conversions.create_index([("chat_id", ASCENDING)])
    db.conversions.create_index([("created_at", ASCENDING)])
    log.info("MongoDB indexes ready.")


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def upsert_user(chat_id: int, username: str = None, first_name: str = None):
    now = datetime.now(timezone.utc)
    _db().users.update_one(
        {"chat_id": chat_id},
        {
            "$set":         {"username": username, "first_name": first_name, "last_seen": now},
            "$setOnInsert": {"first_seen": now, "total_conversions": 0},
        },
        upsert=True,
    )


def increment_conversions(chat_id: int):
    _db().users.update_one(
        {"chat_id": chat_id},
        {"$inc": {"total_conversions": 1}},
    )


def get_user_stats(chat_id: int) -> dict:
    doc = _db().users.find_one({"chat_id": chat_id}, {"_id": 0})
    if doc:
        return {"total": doc.get("total_conversions", 0), "since": doc.get("first_seen")}
    return {"total": 0, "since": None}


# ---------------------------------------------------------------------------
# Conversion log helpers
# ---------------------------------------------------------------------------

def log_conversion(chat_id: int, msg_id: int, file_id: str,
                   file_name: str = None) -> str:
    """Insert a conversion doc and return its string id."""
    result = _db().conversions.insert_one({
        "chat_id":    chat_id,
        "msg_id":     msg_id,
        "file_id":    file_id,
        "file_name":  file_name,
        "status":     "pending",
        "created_at": datetime.now(timezone.utc),
        "finished_at": None,
    })
    return str(result.inserted_id)


def finish_conversion(doc_id: str, status: str = "done"):
    from bson import ObjectId
    _db().conversions.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {"status": status, "finished_at": datetime.now(timezone.utc)}},
    )
