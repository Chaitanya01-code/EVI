from typing import Any, Dict

from app.agents.base.base_agent import BaseAgent
from app.agents.desktop.executor import execute_plan
from app.agents.desktop.planner import build_plan
from app.agents.desktop.verifier import verify_plan
from app.task.task_models import StructuredTask, TaskExecutionResult, TaskStatus


class DesktopAgent(BaseAgent):
    name = "desktop"

    def plan(self, task: StructuredTask) -> Dict[str, Any]:
        return build_plan(task)

    def execute(self, task: StructuredTask, plan: Dict[str, Any]) -> TaskExecutionResult:
        execution = execute_plan(plan)
        return TaskExecutionResult(
            success=execution["success"],
            verified=execution.get("verified", False),
            message=execution["message"],
            status=TaskStatus.VERIFYING,
            agent=self.__class__.__name__,
            task=task,
        )

    def verify(self, task: StructuredTask, result: TaskExecutionResult) -> TaskExecutionResult:
        if result.success and not verify_plan(self.plan(task), {"success": result.success, "verified": result.verified}):
            result.success = False
            result.verified = False
            action = task.action.replace("_application", "").replace("_", " ")
            result.message = f"I couldn't verify that {task.target} {action}."
            result.status = TaskStatus.FAILED
        elif result.success:
            result.verified = True
            result.status = TaskStatus.COMPLETED
        else:
            result.status = TaskStatus.FAILED
        return result
