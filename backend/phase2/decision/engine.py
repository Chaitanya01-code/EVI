from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DecisionOutcome(str, Enum):
    SAFE = "safe"
    RESEARCH_REQUIRED = "research_required"
    USER_APPROVAL_REQUIRED = "user_approval_required"
    BLOCKED = "blocked"


class DecisionEvaluation(BaseModel):
    outcome: DecisionOutcome = DecisionOutcome.SAFE
    reason: str = ""
    needs_research: bool = False
    approval_required: bool = False
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)
    suggested_next_actions: List[str] = Field(default_factory=list)


def evaluate_decision(question: str, state: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> DecisionEvaluation:
    text = (question or "").lower()
    normalized_state = state or {}
    if hasattr(normalized_state, "model_dump"):
        normalized_state = normalized_state.model_dump(mode="json")

    high_impact = any(keyword in text for keyword in ("deploy", "release", "approve", "production", "destroy", "delete all", "shutdown", "restart"))
    has_problem = bool(normalized_state.get("current_problem") or (context or {}).get("current_problem"))
    has_pending = bool(normalized_state.get("pending_decisions") or (context or {}).get("pending_decisions"))

    if high_impact or has_pending:
        return DecisionEvaluation(
            outcome=DecisionOutcome.USER_APPROVAL_REQUIRED,
            reason="This action is high impact and should not proceed without explicit user approval.",
            needs_research=True,
            approval_required=True,
            confidence=0.97,
            evidence=["high-impact action word detected", "pending decision state present"],
            suggested_next_actions=[
                "Confirm the exact action and target with the user.",
                "Review the current work context and recent failure signals.",
                "Pause execution until approval is granted.",
            ],
        )

    if has_problem:
        return DecisionEvaluation(
            outcome=DecisionOutcome.RESEARCH_REQUIRED,
            reason="There is an active problem in the current work state; the system should research before acting.",
            needs_research=True,
            approval_required=False,
            confidence=0.82,
            evidence=["current_problem exists"],
            suggested_next_actions=["Inspect the failing condition and relevant project context.", "Collect the minimal facts needed before proceeding."],
        )

    return DecisionEvaluation(
        outcome=DecisionOutcome.SAFE,
        reason="The request does not trigger a high-impact or uncertain path.",
        needs_research=False,
        approval_required=False,
        confidence=0.72,
        evidence=["no high-impact or uncertain conditions detected"],
        suggested_next_actions=["Proceed with the normal workflow."],
    )
