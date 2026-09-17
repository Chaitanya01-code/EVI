from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class InquiryLimits:
    max_questions_per_task: int = 5
    max_unresolved_questions: int = 3
    max_research_attempts_per_question: int = 2
    max_research_depth: int = 2
    max_question_repeats: int = 2
    inquiry_timeout_seconds: int = 180
    question_cooldown_seconds: int = 30
    active_questions: Dict[str, int] = field(default_factory=dict)

    def check_limits(self, task_id: str, question_count: int) -> bool:
        if question_count > self.max_questions_per_task:
            return True
        current = self.active_questions.get(task_id, 0)
        return current > self.max_unresolved_questions

    def record_question(self, task_id: str) -> None:
        self.active_questions[task_id] = self.active_questions.get(task_id, 0) + 1

    def clear_task(self, task_id: str) -> None:
        self.active_questions.pop(task_id, None)


DEFAULT_INQUIRY_LIMITS = InquiryLimits()
