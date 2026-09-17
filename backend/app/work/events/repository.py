from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database.connection import get_connection
from app.work.events.models import WorkEvent


class WorkEventRepository:
    def __init__(self, table_name: str = "work_events") -> None:
        self.table_name = table_name

    def ensure_schema(self) -> None:
        with get_connection() as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id BIGSERIAL PRIMARY KEY,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    project_id TEXT,
                    project_name TEXT,
                    workspace_path TEXT,
                    application TEXT,
                    file_path TEXT,
                    branch TEXT,
                    command TEXT,
                    exit_code INTEGER,
                    output_summary TEXT,
                    event_metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    timestamp TIMESTAMPTZ NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS {self.table_name}_timestamp_idx ON {self.table_name}(timestamp DESC);
                CREATE INDEX IF NOT EXISTS {self.table_name}_project_idx ON {self.table_name}(project_name);
                CREATE INDEX IF NOT EXISTS {self.table_name}_type_idx ON {self.table_name}(event_type);
                CREATE INDEX IF NOT EXISTS {self.table_name}_source_idx ON {self.table_name}(source);
                CREATE INDEX IF NOT EXISTS {self.table_name}_user_idx ON {self.table_name}(user_id);
                CREATE INDEX IF NOT EXISTS {self.table_name}_session_idx ON {self.table_name}(session_id);
                """
            )

    def save_event(self, event: WorkEvent) -> WorkEvent:
        self.ensure_schema()
        with get_connection() as connection:
            connection.execute(
                f"""
                INSERT INTO {self.table_name}
                (event_id, event_type, source, user_id, session_id, project_id, project_name,
                 workspace_path, application, file_path, branch, command, exit_code,
                 output_summary, event_metadata, timestamp, confidence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO UPDATE SET
                    event_type = EXCLUDED.event_type,
                    source = EXCLUDED.source,
                    project_name = EXCLUDED.project_name,
                    workspace_path = EXCLUDED.workspace_path,
                    application = EXCLUDED.application,
                    file_path = EXCLUDED.file_path,
                    branch = EXCLUDED.branch,
                    command = EXCLUDED.command,
                    exit_code = EXCLUDED.exit_code,
                    output_summary = EXCLUDED.output_summary,
                    event_metadata = EXCLUDED.event_metadata,
                    timestamp = EXCLUDED.timestamp,
                    confidence = EXCLUDED.confidence
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.source,
                    event.user_id,
                    event.session_id,
                    event.project_id,
                    event.project_name,
                    event.workspace_path,
                    event.application,
                    event.file_path,
                    event.branch,
                    event.command,
                    event.exit_code,
                    event.output_summary,
                    json.dumps(event.metadata, default=str),
                    event.timestamp,
                    event.confidence,
                    event.created_at,
                ),
            )
        return event

    def list_recent(self, project_name: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        self.ensure_schema()
        with get_connection() as connection:
            if project_name:
                rows = connection.execute(
                    f"SELECT event_id, event_type, source, user_id, session_id, project_id, project_name, workspace_path, application, file_path, branch, command, exit_code, output_summary, event_metadata, timestamp, confidence FROM {self.table_name} WHERE project_name = %s ORDER BY timestamp DESC LIMIT %s",
                    (project_name, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    f"SELECT event_id, event_type, source, user_id, session_id, project_id, project_name, workspace_path, application, file_path, branch, command, exit_code, output_summary, event_metadata, timestamp, confidence FROM {self.table_name} ORDER BY timestamp DESC LIMIT %s",
                    (limit,),
                ).fetchall()
        return [
            {
                "event_id": row[0],
                "event_type": row[1],
                "source": row[2],
                "user_id": row[3],
                "session_id": row[4],
                "project_id": row[5],
                "project_name": row[6],
                "workspace_path": row[7],
                "application": row[8],
                "file_path": row[9],
                "branch": row[10],
                "command": row[11],
                "exit_code": row[12],
                "output_summary": row[13],
                "metadata": row[14],
                "timestamp": row[15],
                "confidence": row[16],
            }
            for row in rows
        ]
