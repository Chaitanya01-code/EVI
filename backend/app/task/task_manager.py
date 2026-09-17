from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.task.task_models import (
    AgentStatus,
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
        self._active_task_keys: set[tuple[str, str, str, str]] = set()

    def _task_key(self, task: StructuredTask) -> tuple[str, str, str, str]:
        return (task.session_id, task.task_type.value, task.action, task.target or "")

    def is_equivalent_active_task(self, task: StructuredTask) -> bool:
        try:
            from app.database.connection import get_connection

            constraints = [
                task.session_id,
                task.task_type.value,
                task.action,
                task.target,
            ]
            with get_connection() as connection:
                row = connection.execute(
                    """
                    SELECT task_id
                    FROM task_history
                    WHERE session_id = %s
                      AND task_type = %s
                      AND action = %s
                      AND target = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled', 'blocked')
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    constraints,
                ).fetchone()
            return row is not None
        except Exception:
            return False

    def execute(self, task: StructuredTask) -> TaskExecutionResult:
        key = self._task_key(task)
        if key in self._active_task_keys and self._active_task_keys != {key}:
            return TaskExecutionResult(
                success=False,
                verified=False,
                message="An equivalent task is already in progress for this session.",
                status=TaskStatus.BLOCKED,
                agent="orchestrator",
                agent_status=AgentStatus.ASSIGNED,
                task=task,
                output={"blocked": True, "task_id": task.task_id},
            )

        self._active_task_keys.add(key)
        try:
            if self.is_equivalent_active_task(task):
                return TaskExecutionResult(
                    success=False,
                    verified=False,
                    message="An equivalent task is already in progress for this session.",
                    status=TaskStatus.BLOCKED,
                    agent="orchestrator",
                    agent_status=AgentStatus.ASSIGNED,
                    task=task,
                    output={"blocked": True, "task_id": task.task_id},
                )

            task.status = TaskStatus.QUEUED
            task.agent_status = AgentStatus.UNASSIGNED
            if task.task_type == TaskType.MULTI_STEP:
                task.agent_status = AgentStatus.ASSIGNED
                result = self.orchestrator.run(task)
                result.agent_status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
                task.status = result.status
                task.agent_status = result.agent_status
                if self.event_callback:
                    self.event_callback({"event": "task_completed" if result.success else "task_failed", "task_id": task.task_id, "agent": result.agent, "status": result.status.value, "success": result.success})
                return result

            agent = self.router.route(task)
            if agent is None:
                task.status = TaskStatus.FAILED
                task.agent_status = AgentStatus.UNASSIGNED
                return TaskExecutionResult(
                    success=False,
                    message="I couldn't identify the right agent for that task. Could you clarify what you want me to do?",
                    status=TaskStatus.FAILED,
                    agent="unknown",
                    agent_status=AgentStatus.UNASSIGNED,
                    task=task,
                )
            task.agent_status = AgentStatus.ASSIGNED
            if self.event_callback:
                self.event_callback({"event": "task_started", "task_id": task.task_id, "status": "running", "agent": agent.__class__.__name__})
            task.status = TaskStatus.RUNNING
            task.agent_status = AgentStatus.RUNNING
            result = agent.run(task)
            result.agent_status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
            task.status = result.status
            task.agent_status = result.agent_status
            if self.event_callback:
                self.event_callback({"event": "task_completed" if result.success else "task_failed", "task_id": task.task_id, "agent": result.agent, "status": result.status.value, "success": result.success})
            return result
        finally:
            self._active_task_keys.discard(key)
