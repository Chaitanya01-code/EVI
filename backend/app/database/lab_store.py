from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.database.connection import get_connection


def _where(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    clauses = []
    values: List[Any] = []
    for column in ("status", "agent_type", "task_type", "user_id"):
        value = filters.get(column)
        if value:
            clauses.append(f"{column} = %s")
            values.append(value)
    if filters.get("date_from"):
        clauses.append("timestamp >= %s")
        values.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("timestamp <= %s")
        values.append(filters["date_to"])
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


def _task(row: tuple) -> Dict[str, Any]:
    keys = ("task_id", "session_id", "user_id", "task_type", "agent", "category", "action", "target", "status", "success", "verified", "message", "original_text", "input_type", "arguments", "error", "created_at", "started_at", "completed_at", "timestamp")
    return dict(zip(keys, row))


def list_tasks(limit: int, offset: int, filters: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    where, values = _where(filters)
    with get_connection() as connection:
        total = connection.execute(f"SELECT COUNT(*) FROM task_history{where}", values).fetchone()[0]
        rows = connection.execute(
            f"SELECT task_id, session_id, user_id, task_type, agent_type, category, action, target, status, success, verified, message, original_text, input_type, arguments, error, created_at, started_at, completed_at, timestamp FROM task_history{where} ORDER BY timestamp DESC LIMIT %s OFFSET %s",
            values + [limit, offset],
        ).fetchall()
    return [_task(row) for row in rows], total


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    where, values = _where({})
    with get_connection() as connection:
        row = connection.execute(
            "SELECT task_id, session_id, user_id, task_type, agent_type, category, action, target, status, success, verified, message, original_text, input_type, arguments, error, created_at, started_at, completed_at, timestamp FROM task_history WHERE task_id = %s",
            (task_id,),
        ).fetchone()
    return _task(row) if row else None


def list_steps(task_id: str) -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT step_id, agent_type, action, status, success, verified, result, error, started_at, completed_at, timestamp FROM task_history_steps WHERE task_id = %s ORDER BY id",
            (task_id,),
        ).fetchall()
    keys = ("step_id", "agent", "action", "status", "success", "verified", "result", "error", "started_at", "completed_at", "timestamp")
    return [dict(zip(keys, row)) for row in rows]


def list_conversations(limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    with get_connection() as connection:
        total = connection.execute("SELECT COUNT(DISTINCT session_id) FROM conversation_history").fetchone()[0]
        rows = connection.execute(
            """SELECT session_id, MIN(user_id), COUNT(*), (array_agg(user_message ORDER BY timestamp DESC))[1], MIN(timestamp), MAX(timestamp)
               FROM conversation_history GROUP BY session_id ORDER BY MAX(timestamp) DESC LIMIT %s OFFSET %s""",
            (limit, offset),
        ).fetchall()
    return [dict(conversation_id=row[0], session_id=row[0], user_id=row[1], message_count=row[2], last_message=row[3], created_at=row[4], updated_at=row[5]) for row in rows], total


def conversation_messages(session_id: str, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    with get_connection() as connection:
        total = connection.execute("SELECT COUNT(*) FROM conversation_history WHERE session_id = %s", (session_id,)).fetchone()[0]
        rows = connection.execute(
            "SELECT id, session_id, user_id, user_message, input_type, response_type, intent, mode, action, target, confidence, status, evi_response, timestamp FROM conversation_history WHERE session_id = %s ORDER BY timestamp LIMIT %s OFFSET %s",
            (session_id, limit, offset),
        ).fetchall()
    keys = ("id", "session_id", "user_id", "user_message", "input_type", "response_type", "intent", "mode", "action", "target", "confidence", "status", "response", "timestamp")
    return [dict(zip(keys, row)) for row in rows], total


def list_memories(limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    with get_connection() as connection:
        patterns = ["%password%", "%secret%", "%token%", "%api_key%", "%credential%"]
        total = connection.execute("SELECT COUNT(*) FROM memories WHERE key NOT ILIKE ANY(%s)", (patterns,)).fetchone()[0]
        rows = connection.execute(
            "SELECT id, key, value, memory_type, created_at, updated_at FROM memories WHERE key NOT ILIKE ANY(%s) ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (patterns, limit, offset),
        ).fetchall()
    keys = ("id", "key", "value", "memory_type", "created_at", "updated_at")
    return [dict(zip(keys, row)) for row in rows], total


def overview_counts() -> Dict[str, int]:
    with get_connection() as connection:
        task_counts = connection.execute("SELECT status, COUNT(*) FROM task_history GROUP BY status").fetchall()
        conversations = connection.execute("SELECT COUNT(*) FROM conversation_history").fetchone()[0]
        memories = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    counts = {str(status): count for status, count in task_counts}
    return {"running_tasks": counts.get("executing", 0) + counts.get("verifying", 0), "completed_tasks": counts.get("completed", 0), "failed_tasks": counts.get("failed", 0), "conversations": conversations, "memories": memories}
