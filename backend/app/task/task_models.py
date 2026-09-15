from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    DESKTOP = "desktop"
    CODING = "coding"
    CLOUD = "cloud"
    BROWSER = "browser"
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
    action: str
    target: str = ""
    status: TaskStatus = TaskStatus.PENDING
    confidence: float = Field(default=0, ge=0, le=1)


class TaskExecutionResult(BaseModel):
    success: bool
    message: str
    status: TaskStatus
    agent: str
    task: Optional[StructuredTask] = None
