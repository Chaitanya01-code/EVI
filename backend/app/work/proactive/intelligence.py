from __future__ import annotations

from typing import Any, Dict, List

from app.work.proactive.models import ProactiveOpportunity


class ProactiveIntelligence:
    def detect(self, state: Dict[str, Any]) -> List[ProactiveOpportunity]:
        opportunities: List[ProactiveOpportunity] = []
        problem = state.get("current_problem") or ""
        if problem:
            opportunities.append(ProactiveOpportunity(
                type="failure_detected",
                reason=problem,
                confidence=0.97,
                requires_user_decision=False,
                metadata={"source": "current_work_state"},
            ))
        return opportunities
