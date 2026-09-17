from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InquiryContext(BaseModel):
    task_id: str
    goal: str = ""
    state: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    current_work_state: Dict[str, Any] = Field(default_factory=dict)
    memory: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    task_history: List[Dict[str, Any]] = Field(default_factory=list)
    previous_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    project_files: List[str] = Field(default_factory=list)
    project_config: Dict[str, Any] = Field(default_factory=dict)
    project_state: Dict[str, Any] = Field(default_factory=dict)
    knowledge: List[str] = Field(default_factory=list)
    user_instructions: List[str] = Field(default_factory=list)
    http_references: List[str] = Field(default_factory=list)
    requires_user_input: bool = False
    unresolved_questions: List[str] = Field(default_factory=list)
