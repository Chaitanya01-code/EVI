from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuestionCategory(str, Enum):
    missing_requirement = "missing_requirement"
    technical_information = "technical_information"
    project_information = "project_information"
    environment_information = "environment_information"
    dependency_information = "dependency_information"
    error_information = "error_information"
    architecture_information = "architecture_information"
    user_preference = "user_preference"
    authorization = "authorization"
    destructive_action_confirmation = "destructive_action_confirmation"
    deployment_decision = "deployment_decision"
    feature_decision = "feature_decision"


class QuestionPriority(str, Enum):
    optional = "optional"
    useful = "useful"
    required = "required"
    high = "high"
    critical = "critical"


class InquiryQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: "q_" + str(abs(hash(datetime.now(timezone.utc))))[:12])
    task_id: str
    question: str
    purpose: str
    category: QuestionCategory
    priority: QuestionPriority = QuestionPriority.required
    importance: str = "medium"
    source: str = "self_generated"
    status: str = "generated"
    answer: Optional[str] = None
    confidence: float = 0.0
    requires_user: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    options: List[str] = Field(default_factory=list)

    def mark_resolved(self, answer: Optional[str], confidence: float = 0.0) -> None:
        self.answer = answer
        self.confidence = confidence
        self.status = "resolved"
        self.resolved_at = datetime.now(timezone.utc)
