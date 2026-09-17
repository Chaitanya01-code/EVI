from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProactiveOpportunity(BaseModel):
    type: str
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_user_decision: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProactiveSignal(BaseModel):
    signal_type: str
    details: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_user_decision: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
