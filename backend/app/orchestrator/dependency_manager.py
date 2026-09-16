from __future__ import annotations

from typing import Dict, List

from app.orchestrator.models import ExecutionPlan, StepStatus, TaskStep


class DependencyManager:
    def __init__(self, plan: ExecutionPlan) -> None:
        self.plan = plan
        self.steps: Dict[str, TaskStep] = {step.step_id: step for step in plan.steps}

    def ready_steps(self) -> List[TaskStep]:
        ready = []
        for step in self.steps.values():
            if step.status != StepStatus.PENDING:
                continue
            dependencies = [self.steps.get(dependency.step_id) for dependency in step.depends_on]
            if any(dependency is None or dependency.status in {StepStatus.FAILED, StepStatus.CANCELLED, StepStatus.SKIPPED} for dependency in dependencies):
                step.status = StepStatus.SKIPPED
                step.error = "A required dependency failed or was skipped."
                continue
            if all(dependency and dependency.status == required.required_status for dependency, required in zip(dependencies, step.depends_on)):
                step.status = StepStatus.READY
                ready.append(step)
        return ready

    def has_pending(self) -> bool:
        return any(step.status in {StepStatus.PENDING, StepStatus.READY, StepStatus.RUNNING, StepStatus.WAITING} for step in self.steps.values())

    def blocked_steps(self) -> List[TaskStep]:
        return [step for step in self.steps.values() if step.status == StepStatus.SKIPPED]
