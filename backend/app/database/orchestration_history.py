from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskStepRecord(BaseModel):
    task_id: str
    step_id: str
    agent_type: str
    action: str
    status: str
    success: bool
    verified: bool
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def as_db_values(self) -> tuple[Any, ...]:
        return (
            self.task_id,
            self.step_id,
            self.agent_type,
            self.action,
            self.status,
            self.success,
            self.verified,
            json.dumps(self.result, default=str),
            self.error,
            self.started_at,
            self.completed_at,
            self.timestamp,
        )