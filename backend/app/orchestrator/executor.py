from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List

from app.orchestrator.context_manager import ContextManager
from app.orchestrator.coordinator import Coordinator
from app.orchestrator.dependency_manager import DependencyManager
from app.orchestrator.models import ExecutionContext, ExecutionPlan, StepStatus, TaskStep
from app.orchestrator.result_manager import ResultManager
from app.orchestrator.retry_manager import RetryManager


class PlanExecutor:
    def __init__(self, coordinator: Coordinator, max_retries: int = 2) -> None:
        self.coordinator = coordinator
        self.context_manager = ContextManager()
        self.result_manager = ResultManager()
        self.retry_manager = RetryManager(max_retries=max_retries)

    def _run_step(self, step: TaskStep, context: ExecutionContext) -> TaskStep:
        step.status = StepStatus.RUNNING
        self.coordinator.emit(context, {"agent": step.agent_type, "action": step.action, "step_id": step.step_id, "status": "running"})
        result = self.retry_manager.run(step, lambda: self.coordinator.execute(step, context))
        self.result_manager.record(step, result, context)
        self.coordinator.emit(context, {"agent": step.agent_type, "action": step.action, "step_id": step.step_id, "status": step.status.value, "success": result.success})
        return step

    def run(self, plan: ExecutionPlan, context: ExecutionContext) -> List[TaskStep]:
        dependencies = DependencyManager(plan)
        while dependencies.has_pending():
            ready = dependencies.ready_steps()
            if not ready:
                break
            for step in ready:
                self.context_manager.prepare_step(step, context)
                step.started_at = datetime.now(timezone.utc)
            if len(ready) == 1:
                self._run_step(ready[0], context)
            else:
                with ThreadPoolExecutor(max_workers=min(len(ready), 4)) as pool:
                    futures = [pool.submit(self._run_step, step, context) for step in ready]
                    for future in as_completed(futures):
                        future.result()
            for step in ready:
                step.completed_at = datetime.now(timezone.utc)
        for step in plan.steps:
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.SKIPPED
                step.error = "Step dependencies could not be satisfied."
        return plan.steps
