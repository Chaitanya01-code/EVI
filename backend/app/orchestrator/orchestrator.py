from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.orchestrator.coordinator import Coordinator
from app.orchestrator.executor import PlanExecutor
from app.orchestrator.models import ExecutionContext, OrchestrationResult, StepStatus
from app.orchestrator.planner import build_plan
from app.orchestrator.result_manager import ResultManager
from app.orchestrator.verifier import OrchestrationVerifier
from app.task.task_models import StructuredTask, TaskExecutionResult, TaskStatus
from app.task.task_router import TaskRouter


class MultiAgentOrchestrator:
    def __init__(self, router: TaskRouter, event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.router = router
        self.event_callback = event_callback
        self.verifier = OrchestrationVerifier()
        self.result_manager = ResultManager()

    def run(self, task: StructuredTask) -> TaskExecutionResult:
        plan = build_plan(task)
        context = ExecutionContext(
            task_id=task.task_id,
            user_id=task.user_id,
            session_id=task.session_id,
            original_request=task.original_text,
            input_type=task.input_type,
            execution_state="executing",
        )
        coordinator = Coordinator(self.router, self.event_callback)
        steps = PlanExecutor(coordinator).run(plan, context)
        verified = self.verifier.verify_plan(steps)
        success = bool(steps) and all(step.status == StepStatus.COMPLETED for step in steps)
        message = self.result_manager.summarize(steps)
        context.execution_state = "completed" if success and verified else "failed"
        status = TaskStatus.COMPLETED if success and verified else TaskStatus.FAILED
        if any(step.status == StepStatus.WAITING for step in steps):
            status = TaskStatus.AWAITING_PERMISSION
        task.status = status
        return TaskExecutionResult(
            success=success and verified,
            verified=verified,
            message=message,
            status=status,
            agent="orchestrator",
            task=task,
            output={
                "steps": [step.model_dump() for step in steps],
                "events": context.events,
                "variables": context.variables,
            },
        )
