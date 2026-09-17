from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.phase3.inquiry.inquiry_engine import InquiryEngine
from app.phase3.user_questions.answer_handler import AnswerHandler
from app.phase3.user_questions.question_presenter import QuestionPresenter


class InquiryCoordinator:
    def __init__(self) -> None:
        self.engine = InquiryEngine()
        self.presenter = QuestionPresenter()
        self.answer_handler = AnswerHandler()

    def start(self, task: Dict[str, Any]) -> List[Any]:
        return self.engine.start(task)

    def get_required_information(self, task: Dict[str, Any]) -> List[Any]:
        return self.engine.get_required_information(task)

    def generate_question(self, task: Dict[str, Any], category: str = "missing_requirement") -> Any:
        return self.engine.generate_question(task, category)

    def resolve_question(self, task_id: str, question_id: str, answer: Optional[str], confidence: float = 0.0) -> Any:
        return self.engine.resolve_question(task_id, question_id, answer, confidence)

    def request_user_decision(self, task_id: str, question: str, options: Optional[List[str]] = None, category: str = "feature_decision") -> Any:
        return self.engine.request_user_decision(task_id, question, options, category)

    def resume_after_answer(self, task_id: str, question_id: str, answer: str, confidence: float = 0.9) -> Any:
        return self.engine.resume_after_answer(task_id, question_id, answer, confidence)
