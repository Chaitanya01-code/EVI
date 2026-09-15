from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from pathlib import Path

from app.database.models import ConversationRecord

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "evi.db"
DB_URL = os.getenv("DB_URL", "")
DB_PATH = Path(os.getenv("EVI_SQLITE_PATH", str(_DEFAULT_DB)))


def _connection() -> sqlite3.Connection:
    if DB_URL and not DB_URL.startswith("sqlite"):
        logger.warning("DB_URL is not a supported local SQLite URL; using EVI_SQLITE_PATH")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            input_type TEXT NOT NULL,
            intent TEXT NOT NULL,
            mode TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL,
            evi_response TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def save_record(record: ConversationRecord) -> None:
    connection = _connection()
    try:
        connection.execute(
            """
            INSERT INTO conversation_history
            (session_id, user_message, input_type, intent, mode, action, target,
             confidence, status, evi_response, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            record.as_db_values(),
        )
        connection.commit()
    finally:
        connection.close()


async def save_record_async(record: ConversationRecord) -> None:
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_record, record)
    except Exception:
        logger.exception("Unable to persist conversation record")
