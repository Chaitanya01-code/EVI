from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.orchestrator.models import AgentResult, AgentRequest, ExecutionContext, StepStatus, TaskStep
from app.task.task_models import StructuredTask, TaskType
from app.task.task_router import TaskRouter


_PROTECTED_ACTIONS = {
    "shutdown", "restart", "sleep", "delete_file", "delete_folder", "push",
    "commit", "deploy", "rollback", "terraform_apply", "modify_iam",
    "install_dependency",
}


class Coordinator:
    def __init__(self, router: TaskRouter, event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.router = router
        self.event_callback = event_callback

    def emit(self, context: ExecutionContext, event: Dict[str, Any]) -> None:
        if "event" not in event:
            status = event.get("status", "update")
            event["event"] = {
                "running": "step_started",
                "completed": "step_completed",
                "failed": "step_failed",
                "waiting": "step_waiting",
            }.get(status, "step_updated")
            event["task_id"] = context.task_id
        context.events.append(event)
        if self.event_callback:
            self.event_callback(event)

    def _policy_denied(self, step: TaskStep, context: ExecutionContext) -> Optional[str]:
        approved = bool(context.permissions.get(step.step_id) or context.permissions.get(step.action))
        if step.action in _PROTECTED_ACTIONS and not approved:
            return f"Action '{step.action}' requires user confirmation before execution."
        return None

    def execute(self, step: TaskStep, context: ExecutionContext) -> AgentResult:
        context.current_step = step.step_id
        denied = self._policy_denied(step, context)
        if denied:
            return AgentResult(
                task_id=step.task_id, step_id=step.step_id, agent=step.agent_type,
                action=step.action, status=StepStatus.WAITING, success=False,
                error=denied, message=denied,
            )
        try:
            task_type = TaskType(step.agent_type)
            agent = self.router.route(StructuredTask(
                task_id=step.task_id, user_id=context.user_id, session_id=context.session_id,
                input_type=context.input_type, original_text=step.description,
                task_type=task_type, category=step.arguments.get("category", ""),
                action=step.action, target=step.target,
            ))
            if agent is None:
                raise ValueError(f"No agent is registered for '{step.agent_type}'.")
            task = StructuredTask(
                task_id=step.task_id,
                user_id=context.user_id,
                session_id=context.session_id,
                input_type=context.input_type,
                original_text=step.description,
                task_type=task_type,
                category=step.arguments.get("category", ""),
                action=step.action,
                target=step.target,
            )
            result = agent.run(task)
            output = dict(result.output)
            output.pop("message", None)
            output.pop("success", None)
            output.pop("verified", None)
            return AgentResult(
                task_id=step.task_id, step_id=step.step_id, agent=step.agent_type,
                action=step.action,
                status=StepStatus.COMPLETED if result.success and result.verified else StepStatus.FAILED,
                success=result.success, verified=result.verified, output=output,
                error=None if result.success else result.message,
                message=result.message,
                next_context=output,
            )
        except Exception as error:
            return AgentResult(
                task_id=step.task_id, step_id=step.step_id, agent=step.agent_type,
                action=step.action, status=StepStatus.FAILED, success=False,
                error=str(error), message="The agent failed to execute this step.",
            )
