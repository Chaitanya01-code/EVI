from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    RESEARCH_MORE = "RESEARCH_MORE"
    USER_REQUIRED = "USER_REQUIRED"
    UNKNOWN = "UNKNOWN"


class ResolutionResult(BaseModel):
    status: ResolutionStatus = ResolutionStatus.UNKNOWN
    answer: Optional[str] = None
    confidence: float = 0.0
    source: str = "unknown"
    sources: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
