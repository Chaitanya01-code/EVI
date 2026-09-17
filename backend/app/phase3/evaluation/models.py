from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationStatus(str, Enum):
    RESOLVED = "RESOLVED"
    RESEARCH_MORE = "RESEARCH_MORE"
    USER_REQUIRED = "USER_REQUIRED"
    UNKNOWN = "UNKNOWN"


class EvaluationResult(BaseModel):
    status: EvaluationStatus = EvaluationStatus.UNKNOWN
    relevant: bool = False
    complete: bool = False
    confidence: float = 0.0
    conflicts: List[str] = Field(default_factory=list)
    requires_user_confirmation: bool = False
    additional_research_needed: bool = False
    summary: str = ""
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
