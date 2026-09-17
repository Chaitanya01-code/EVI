from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserQuestionStatus(str, Enum):
    pending = "pending"
    answered = "answered"
    cancelled = "cancelled"


class UserQuestion(BaseModel):
    question_id: str
    task_id: str
    message: str
    options: List[str] = Field(default_factory=list)
    status: UserQuestionStatus = UserQuestionStatus.pending
    answer: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    answered_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
