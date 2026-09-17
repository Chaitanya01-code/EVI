from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.phase3.inquiry.models import InquiryQuestion


class QuestionManager:
    def __init__(self) -> None:
        self._questions: Dict[str, List[InquiryQuestion]] = {}

    def add_question(self, task_id: str, question: InquiryQuestion) -> InquiryQuestion:
        self._questions.setdefault(task_id, []).append(question)
        return question

    def get_active_questions(self, task_id: str) -> List[InquiryQuestion]:
        return self._questions.get(task_id, [])

    def resolve_question(self, task_id: str, question_id: str, answer: Optional[str], confidence: float = 0.0) -> Optional[InquiryQuestion]:
        for question in self._questions.get(task_id, []):
            if question.question_id == question_id:
                question.mark_resolved(answer, confidence)
                return question
        return None

    def get_unique_questions(self, task_id: str, question: InquiryQuestion) -> bool:
        for existing in self._questions.get(task_id, []):
            if existing.question == question.question:
                return False
        return True
