from typing import Any, Dict

from app.agents.base.base_agent import BaseAgent
from app.agents.coding.executor import execute_plan
from app.agents.coding.planner import build_plan
from app.task.task_models import StructuredTask, TaskExecutionResult, TaskStatus


class CodingAgent(BaseAgent):
    name = "coding"

    def plan(self, task: StructuredTask) -> Dict[str, Any]:
        return build_plan(task)

    def execute(self, task: StructuredTask, plan: Dict[str, Any]) -> TaskExecutionResult:
        execution = execute_plan(plan)
        return TaskExecutionResult(
            success=execution["success"], message=execution["message"],
            status=TaskStatus.FAILED, agent=self.__class__.__name__, task=task,
        )

    def verify(self, task: StructuredTask, result: TaskExecutionResult) -> TaskExecutionResult:
        return result
