from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.task.task_models import AgentStatus, StructuredTask, TaskExecutionResult, TaskStatus


class BaseAgent(ABC):
    name = "base"

    def understand(self, task: StructuredTask) -> StructuredTask:
        return task

    @abstractmethod
    def plan(self, task: StructuredTask) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, task: StructuredTask, plan: Dict[str, Any]) -> TaskExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def verify(self, task: StructuredTask, result: TaskExecutionResult) -> TaskExecutionResult:
        raise NotImplementedError

    def run(self, task: StructuredTask) -> TaskExecutionResult:
        task.status = TaskStatus.PLANNING
        task.agent_status = AgentStatus.ASSIGNED
        plan = self.plan(self.understand(task))
        task.status = TaskStatus.RUNNING
        task.agent_status = AgentStatus.RUNNING
        result = self.execute(task, plan)
        task.status = TaskStatus.VERIFICATION
        task.agent_status = AgentStatus.RUNNING
        verified = self.verify(task, result)
        task.status = verified.status
        task.agent_status = AgentStatus.COMPLETED if verified.success else AgentStatus.FAILED
        return verified
