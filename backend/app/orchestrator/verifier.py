from __future__ import annotations

from typing import List

from app.orchestrator.models import StepStatus, TaskStep


class OrchestrationVerifier:
    def verify_step(self, step: TaskStep) -> bool:
        result = step.result.get("agent_result")
        return bool(result and result.success and result.verified and step.status == StepStatus.COMPLETED)

    def verify_plan(self, steps: List[TaskStep]) -> bool:
        return bool(steps) and all(self.verify_step(step) for step in steps)
