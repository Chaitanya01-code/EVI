from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InformationStatus(str, Enum):
    ALREADY_KNOWN = "already_known"
    DISCOVERABLE = "discoverable"
    USER_DECISION_REQUIRED = "user_decision_required"
    UNKNOWN = "unknown"


class InformationResolution(BaseModel):
    status: InformationStatus = InformationStatus.UNKNOWN
    question: str = ""
    needs_research: bool = False
    approval_required: bool = False
    provenance: List[str] = Field(default_factory=list)
    research_plan: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""
    raw_state: Dict[str, Any] = Field(default_factory=dict)

    def detect_proactive_opportunities(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        state = state or {}
        problems = state.get("current_problem") or ""
        if problems:
            opportunities.append({
                "type": "research_needed",
                "reason": str(problems),
                "confidence": 0.9,
                "requires_user_decision": False,
                "metadata": {"source": "current_problem"},
            })

        pending = state.get("pending_decisions") or []
        if isinstance(pending, str):
            pending = [pending]
        for decision in pending:
            text = str(decision).lower()
            if any(keyword in text for keyword in ("deploy", "release", "approve", "production")):
                opportunities.append({
                    "type": "release_decision",
                    "reason": str(decision),
                    "confidence": 0.96,
                    "requires_user_decision": True,
                    "metadata": {"source": "pending_decisions"},
                })

        recent = state.get("recent_actions") or []
        if isinstance(recent, str):
            recent = [recent]
        recent_text = " ".join(str(item) for item in recent).lower()
        if any(keyword in recent_text for keyword in ("deploy", "rollback", "release")):
            opportunities.append({
                "type": "recovery_monitoring",
                "reason": "Recent actions indicate a deployment or rollback flow that may need supervision.",
                "confidence": 0.76,
                "requires_user_decision": False,
                "metadata": {"source": "recent_actions"},
            })

        if not opportunities and problems:
            opportunities.append({
                "type": "monitoring",
                "reason": "The current work state suggests the system should keep observing before acting.",
                "confidence": 0.49,
                "requires_user_decision": False,
                "metadata": {"source": "current_problem"},
            })

        return opportunities


def _get_work_context_value(context: Optional[Dict[str, Any]], key: str) -> Any:
    if not context:
        return None
    if isinstance(context, dict):
        current = context.get("current_work_state")
        if isinstance(current, dict):
            return current.get(key)
        return context.get(key)
    current = getattr(context, "current_work_state", None)
    if current is not None and hasattr(current, key):
        return getattr(current, key)
    return getattr(context, key, None)


def _normalize_state(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if state is None:
        return {}
    if hasattr(state, "model_dump"):
        return state.model_dump(mode="json")
    if isinstance(state, dict):
        return state
    return dict(state)


def resolve_information(question: str, state: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> InformationResolution:
    normalized_state = _normalize_state(state)
    q = (question or "").strip()
    q_lower = q.lower()

    branch = normalized_state.get("branch") or _get_work_context_value(context, "branch")
    if branch and any(keyword in q_lower for keyword in ("branch", "current branch", "project branch")):
        return InformationResolution(
            status=InformationStatus.ALREADY_KNOWN,
            question=q,
            needs_research=False,
            approval_required=False,
            provenance=[f"state.branch={branch}"],
            confidence=0.98,
            reason="The requested branch information is already present in the current work state.",
            raw_state=normalized_state,
        )

    if any(keyword in q_lower for keyword in ("should i", "can i", "do i", "deploy", "production", "approve", "release")):
        return InformationResolution(
            status=InformationStatus.USER_DECISION_REQUIRED,
            question=q,
            needs_research=True,
            approval_required=True,
            provenance=["needs explicit user approval before high-impact actions."],
            research_plan=[
                "Confirm the deployment target and current release criteria.",
                "Review recent work state and failure signals before acting.",
                "Request explicit approval from the user before executing a high-impact action.",
            ],
            confidence=0.95,
            reason="This is a high-impact action that requires human confirmation and context review.",
            raw_state=normalized_state,
        )

    if normalized_state.get("project") or _get_work_context_value(context, "project"):
        return InformationResolution(
            status=InformationStatus.DISCOVERABLE,
            question=q,
            needs_research=True,
            approval_required=False,
            provenance=["missing fact is not yet in the observed state"],
            research_plan=[
                "Check the project configuration and runtime settings for the missing fact.",
                "Verify the source-of-truth for the service, port, or environment value.",
                "Cross-check the observed work context against the repository or runtime configuration.",
            ],
            confidence=0.84,
            reason="The fact is not currently established, but it should be discoverable from project context.",
            raw_state=normalized_state,
        )

    return InformationResolution(
        status=InformationStatus.UNKNOWN,
        question=q,
        needs_research=True,
        approval_required=False,
        provenance=["no current evidence available"],
        research_plan=["Inspect the current work state and any active repository context for missing facts."],
        confidence=0.35,
        reason="The information is not known yet and requires additional observation before a confident answer is possible.",
        raw_state=normalized_state,
    )
