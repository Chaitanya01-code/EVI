from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from app.database.connection import get_connection
from app.database.models import ConversationRecord, TaskRecord
from app.database.orchestration_history import TaskStepRecord

logger = logging.getLogger(__name__)


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS conversation_history (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id),
                user_message TEXT NOT NULL,
                input_type TEXT NOT NULL,
                response_type TEXT NOT NULL,
                intent TEXT NOT NULL,
                mode TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                status TEXT NOT NULL,
                evi_response TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, key)
            );
            CREATE INDEX IF NOT EXISTS memories_user_id_idx ON memories(user_id);
            CREATE TABLE IF NOT EXISTS task_history (
                id BIGSERIAL PRIMARY KEY,
                task_id TEXT UNIQUE NOT NULL,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id),
                task_type TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                verified BOOLEAN NOT NULL,
                message TEXT NOT NULL,
                original_text TEXT NOT NULL DEFAULT '',
                input_type TEXT NOT NULL DEFAULT 'text',
                arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
                error TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                timestamp TIMESTAMPTZ NOT NULL
            );
            CREATE INDEX IF NOT EXISTS task_history_user_id_idx ON task_history(user_id);
            CREATE INDEX IF NOT EXISTS task_history_task_id_idx ON task_history(task_id);
            ALTER TABLE task_history ADD COLUMN IF NOT EXISTS original_text TEXT NOT NULL DEFAULT '';
            ALTER TABLE task_history ADD COLUMN IF NOT EXISTS input_type TEXT NOT NULL DEFAULT 'text';
            ALTER TABLE task_history ADD COLUMN IF NOT EXISTS arguments JSONB NOT NULL DEFAULT '{}'::jsonb;
            ALTER TABLE task_history ADD COLUMN IF NOT EXISTS error TEXT;
            ALTER TABLE task_history ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
            ALTER TABLE task_history ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
            ALTER TABLE task_history ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
            CREATE TABLE IF NOT EXISTS task_history_steps (
                id BIGSERIAL PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES task_history(task_id) ON DELETE CASCADE,
                step_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                verified BOOLEAN NOT NULL,
                result JSONB NOT NULL DEFAULT '{}'::jsonb,
                error TEXT,
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                timestamp TIMESTAMPTZ NOT NULL,
                UNIQUE (task_id, step_id)
            );
            CREATE INDEX IF NOT EXISTS task_history_steps_task_id_idx ON task_history_steps(task_id);
            """
        )


def ensure_user(user_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO users (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
            (user_id,),
        )


def save_record(record: ConversationRecord) -> None:
    ensure_user(record.user_id)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO conversation_history
            (session_id, user_id, user_message, input_type, response_type, intent, mode,
             action, target, confidence, status, evi_response, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            record.as_db_values(),
        )


def retrieve_memories(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    ensure_user(user_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT key, value, memory_type, confidence
            FROM memories WHERE user_id = %s
            ORDER BY updated_at DESC LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
    return [
        {"key": row[0], "value": row[1], "memory_type": row[2], "confidence": row[3]}
        for row in rows
    ]


def upsert_memory(user_id: str, key: str, value: str, memory_type: str, confidence: float) -> None:
    ensure_user(user_id)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO memories (user_id, key, value, memory_type, confidence)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, key) DO UPDATE SET
                value = EXCLUDED.value, memory_type = EXCLUDED.memory_type,
                confidence = EXCLUDED.confidence, updated_at = NOW()
            """,
            (user_id, key, value, memory_type, confidence),
        )


def delete_memory(user_id: str, key: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM memories WHERE user_id = %s AND key = %s", (user_id, key))


async def initialize_database_async() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, initialize_database)


async def save_record_async(record: ConversationRecord) -> None:
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_record, record)
    except Exception:
        logger.exception("Unable to persist conversation record")


def save_or_update_task_record(record: TaskRecord) -> None:
    ensure_user(record.user_id)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO task_history
            (task_id, session_id, user_id, task_type, agent_type, category,
             action, target, status, success, verified, message, original_text,
             input_type, arguments, error, created_at, started_at, completed_at, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (task_id) DO UPDATE SET
                status = EXCLUDED.status,
                success = EXCLUDED.success,
                verified = EXCLUDED.verified,
                message = EXCLUDED.message,
                original_text = EXCLUDED.original_text,
                input_type = EXCLUDED.input_type,
                arguments = EXCLUDED.arguments,
                error = EXCLUDED.error,
                started_at = EXCLUDED.started_at,
                completed_at = EXCLUDED.completed_at,
                timestamp = EXCLUDED.timestamp
            """,
            record.as_db_values(),
        )


async def save_or_update_task_record_async(record: TaskRecord) -> None:
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_or_update_task_record, record)
    except Exception:
        logger.exception("Unable to persist task history record")


def save_or_update_task_step_record(record: TaskStepRecord) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO task_history_steps
            (task_id, step_id, agent_type, action, status, success, verified,
             result, error, started_at, completed_at, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
            ON CONFLICT (task_id, step_id) DO UPDATE SET
                status = EXCLUDED.status,
                success = EXCLUDED.success,
                verified = EXCLUDED.verified,
                result = EXCLUDED.result,
                error = EXCLUDED.error,
                completed_at = EXCLUDED.completed_at,
                timestamp = EXCLUDED.timestamp
            """,
            record.as_db_values(),
        )


async def save_or_update_task_step_record_async(record: TaskStepRecord) -> None:
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_or_update_task_step_record, record)
    except Exception:
        logger.exception("Unable to persist task step history record")

