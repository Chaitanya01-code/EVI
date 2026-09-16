from __future__ import annotations

from app.task.task_models import (
    StructuredTask,
    TaskExecutionResult,
    TaskStatus,
    TaskType,
)
from app.task.task_router import TaskRouter


class TaskManager:
    def __init__(self, router: TaskRouter) -> None:
        self.router = router

    def execute(self, task: StructuredTask) -> TaskExecutionResult:
        if task.task_type == TaskType.MULTI_STEP:
            task.status = TaskStatus.FAILED
            return TaskExecutionResult(
                success=False,
                verified=False,
                message="This is a multi-step task combining multiple actions. Multi-agent orchestration is required and will be supported in an upcoming update.",
                status=TaskStatus.FAILED,
                agent="orchestrator",
                task=task,
            )
        agent = self.router.route(task)
        if agent is None:
            task.status = TaskStatus.FAILED
            return TaskExecutionResult(
                success=False,
                message="I couldn't identify the right agent for that task. Could you clarify what you want me to do?",
                status=TaskStatus.FAILED,
                agent="unknown",
                task=task,
            )
        return agent.run(task)
