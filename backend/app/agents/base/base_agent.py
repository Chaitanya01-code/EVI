from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.task.task_models import StructuredTask, TaskExecutionResult, TaskStatus


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
        plan = self.plan(self.understand(task))
        task.status = TaskStatus.EXECUTING
        result = self.execute(task, plan)
        task.status = TaskStatus.VERIFYING
        return self.verify(task, result)
