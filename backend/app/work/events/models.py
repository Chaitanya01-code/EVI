from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class WorkEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    source: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    workspace_path: Optional[str] = None
    application: Optional[str] = None
    file_path: Optional[str] = None
    branch: Optional[str] = None
    command: Optional[str] = None
    exit_code: Optional[int] = None
    output_summary: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)

    @property
    def observed(self) -> bool:
        return bool(self.metadata.get("inferred") is not True)

    def as_db_values(self) -> tuple[Any, ...]:
        return (
            self.event_id,
            self.event_type,
            self.source,
            self.user_id,
            self.session_id,
            self.project_id,
            self.project_name,
            self.workspace_path,
            self.application,
            self.file_path,
            self.branch,
            self.command,
            self.exit_code,
            self.output_summary,
            self.metadata,
            self.timestamp.isoformat(),
            self.confidence,
            self.created_at.isoformat(),
        )
