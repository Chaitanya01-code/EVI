from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    DESKTOP = "desktop"
    CODING = "coding"
    CLOUD = "cloud"
    BROWSER = "browser"
    MULTI_STEP = "multi_step"
    UNKNOWN = "unknown"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    AWAITING_PERMISSION = "awaiting_permission"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StructuredTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    session_id: str
    input_type: str
    original_text: str
    task_type: TaskType
    category: str = ""
    action: str
    target: str = ""
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    confidence: float = Field(default=0, ge=0, le=1)


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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


class TaskExecutionResult(BaseModel):
    success: bool
    verified: bool = False
    message: str
    status: TaskStatus
    agent: str
    task: Optional[StructuredTask] = None
    output: Dict[str, Any] = Field(default_factory=dict)
