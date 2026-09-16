from __future__ import annotations

from typing import Callable, TypeVar

from app.orchestrator.models import AgentResult, StepStatus, TaskStep


T = TypeVar("T")


class RetryManager:
    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries

    def run(self, step: TaskStep, operation: Callable[[], AgentResult]) -> AgentResult:
        while True:
            result = operation()
            if result.success or step.retry_count >= self.max_retries:
                return result
            if result.error and "confirmation" in result.error.lower():
                return result
            step.retry_count += 1
            step.status = StepStatus.WAITING
