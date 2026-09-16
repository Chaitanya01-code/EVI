from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ConversationRecord(BaseModel):
    session_id: str
    user_id: str
    user_message: str
    input_type: str
    response_type: str
    intent: str
    mode: str
    action: str
    target: str
    confidence: float
    status: str
    evi_response: str
    timestamp: datetime

    def as_db_values(self) -> tuple[Any, ...]:
        return (
            self.session_id,
            self.user_id,
            self.user_message,
            self.input_type,
            self.response_type,
            self.intent,
            self.mode,
            self.action,
            self.target,
            self.confidence,
            self.status,
            self.evi_response,
            self.timestamp.isoformat(),
        )


class TaskRecord(BaseModel):
    task_id: str
    session_id: str
    user_id: str
    task_type: str
    agent_type: str
    category: str
    action: str
    target: str
    status: str
    success: bool
    verified: bool
    message: str
    original_text: str = ""
    input_type: str = "text"
    arguments: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timestamp: datetime

    def as_db_values(self) -> tuple[Any, ...]:
        return (
            self.task_id,
            self.session_id,
            self.user_id,
            self.task_type,
            self.agent_type,
            self.category,
            self.action,
            self.target,
            self.status,
            self.success,
            self.verified,
            self.message,
            self.original_text,
            self.input_type,
            json.dumps(self.arguments, default=str),
            self.error,
            self.created_at,
            self.started_at,
            self.completed_at,
            self.timestamp.isoformat(),
        )

