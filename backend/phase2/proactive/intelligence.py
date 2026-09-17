from __future__ import annotations

from typing import Any, Dict, List


class ProactiveIntelligence:
    def detect(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.detect_proactive_opportunities(state)

    def detect_proactive_opportunities(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        state = state or {}

        problem = state.get("current_problem") or ""
        if problem:
            opportunities.append({
                "type": "research_needed",
                "reason": str(problem),
                "confidence": 0.91,
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
                    "type": "decision_needed",
                    "reason": str(decision),
                    "confidence": 0.97,
                    "requires_user_decision": True,
                    "metadata": {"source": "pending_decisions"},
                })

        recent = state.get("recent_actions") or []
        if isinstance(recent, str):
            recent = [recent]
        recent_text = " ".join(str(item) for item in recent).lower()
        if any(keyword in recent_text for keyword in ("deploy", "rollback", "release")):
            opportunities.append({
                "type": "state_monitoring",
                "reason": "Recent actions show the user is in a release or recovery workflow.",
                "confidence": 0.74,
                "requires_user_decision": False,
                "metadata": {"source": "recent_actions"},
            })

        return opportunities
