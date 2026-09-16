from typing import Any, Dict

from app.agents.base.base_agent import BaseAgent
from app.agents.coding.executor import execute_plan
from app.agents.coding.planner import build_plan
from app.agents.coding.verifier import verify_plan
from app.task.task_models import StructuredTask, TaskExecutionResult, TaskStatus


class CodingAgent(BaseAgent):
    name = "coding"

    def plan(self, task: StructuredTask) -> Dict[str, Any]:
        return build_plan(task)

    def execute(self, task: StructuredTask, plan: Dict[str, Any]) -> TaskExecutionResult:
        execution = execute_plan(plan)
        return TaskExecutionResult(
            success=execution["success"], verified=execution.get("verified", False), message=execution["message"],
            status=TaskStatus.VERIFYING, agent=self.__class__.__name__, task=task,
        )

    def verify(self, task: StructuredTask, result: TaskExecutionResult) -> TaskExecutionResult:
        if result.success and not verify_plan(self.plan(task), {"success": result.success, "verified": result.verified}):
            result.success = False
            result.verified = False
            result.message = "I couldn't verify that coding action."
            result.status = TaskStatus.FAILED
        elif result.success:
            result.status = TaskStatus.COMPLETED
        else:
            result.status = TaskStatus.FAILED
        return result
