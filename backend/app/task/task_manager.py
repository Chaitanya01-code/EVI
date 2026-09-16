from __future__ import annotations

from app.task.task_models import (
    StructuredTask,
    TaskExecutionResult,
    TaskStatus,
    TaskType,
)
from app.orchestrator.orchestrator import MultiAgentOrchestrator
from app.task.task_router import TaskRouter


class TaskManager:
    def __init__(self, router: TaskRouter) -> None:
        self.router = router
        self.orchestrator = MultiAgentOrchestrator(router)

    def execute(self, task: StructuredTask) -> TaskExecutionResult:
        if task.task_type == TaskType.MULTI_STEP:
            return self.orchestrator.run(task)
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
