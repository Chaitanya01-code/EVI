from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.task.task_models import (
    StructuredTask,
    TaskExecutionResult,
    TaskStatus,
    TaskType,
)
from app.orchestrator.orchestrator import MultiAgentOrchestrator
from app.task.task_router import TaskRouter


class TaskManager:
    def __init__(self, router: TaskRouter, event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.router = router
        self.event_callback = event_callback
        self.orchestrator = MultiAgentOrchestrator(router, event_callback=event_callback)

    def execute(self, task: StructuredTask) -> TaskExecutionResult:
        if self.event_callback:
            self.event_callback({"event": "task_started", "task_id": task.task_id, "status": "running"})
        if task.task_type == TaskType.MULTI_STEP:
            result = self.orchestrator.run(task)
            if self.event_callback:
                self.event_callback({"event": "task_completed" if result.success else "task_failed", "task_id": task.task_id, "status": result.status.value, "success": result.success})
            return result
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
        result = agent.run(task)
        if self.event_callback:
            self.event_callback({"event": "task_completed" if result.success else "task_failed", "task_id": task.task_id, "agent": result.agent, "status": result.status.value, "success": result.success})
        return result
