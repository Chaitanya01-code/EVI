from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CurrentWorkState(BaseModel):
    project: Optional[str] = None
    workspace: Optional[str] = None
    application: Optional[str] = None
    current_file: Optional[str] = None
    branch: Optional[str] = None
    current_task: Optional[str] = None
    current_goal: Optional[str] = None
    current_problem: Optional[str] = None
    recent_actions: List[str] = Field(default_factory=list)
    completed_steps: List[str] = Field(default_factory=list)
    pending_decisions: List[str] = Field(default_factory=list)
    possible_next_actions: List[str] = Field(default_factory=list)
    relevant_research: List[str] = Field(default_factory=list)
    confidence: Dict[str, float] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContextSnapshot(BaseModel):
    current_work: CurrentWorkState
    recent_events: List[Dict[str, Any]] = Field(default_factory=list)
    project_context: Dict[str, Any] = Field(default_factory=dict)
    active_task: Optional[Dict[str, Any]] = None


class ConfidenceProfile(BaseModel):
    project: float = 0.0
    application: float = 0.0
    task: float = 0.0
    goal: float = 0.0
