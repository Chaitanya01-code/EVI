from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Page(BaseModel):
    limit: int
    offset: int
    total: int


class PageResponse(BaseModel):
    data: List[Any]
    pagination: Page
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    components: Dict[str, str]


class EventResponse(BaseModel):
    event: str
    timestamp: datetime
    data: Dict[str, Any] = Field(default_factory=dict)
