from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.phase3.inquiry.inquiry_limits import InquiryLimits
from app.phase3.inquiry.models import InquiryQuestion, QuestionCategory, QuestionPriority
from app.phase3.inquiry.question_generator import QuestionGenerator
from app.phase3.inquiry.question_manager import QuestionManager


class InquiryEngine:
    def __init__(self, max_questions_per_task: int = 5, max_research_attempts_per_question: int = 2) -> None:
        self.generator = QuestionGenerator()
        self.manager = QuestionManager()
        self.limits = InquiryLimits(
            max_questions_per_task=max_questions_per_task,
            max_research_attempts_per_question=max_research_attempts_per_question,
        )

    def start(self, task: Dict[str, Any]) -> List[InquiryQuestion]:
        task_id = str(task.get("task_id") or "unknown-task")
        questions = self.get_required_information(task)
        for question in questions:
            self.manager.add_question(task_id, question)
        return questions

    def get_required_information(self, task: Dict[str, Any]) -> List[InquiryQuestion]:
        state = task.get("state") or {}
        known_terms: Set[str] = set()
        for key, value in state.items():
            if value not in (None, "", False):
                known_terms.add(str(key).lower())
        goal = str(task.get("goal") or "")
        if "rag" in goal.lower() and "vector_store" not in known_terms:
            return self.generator.generate_questions(task, list(known_terms))
        if "rag" in goal.lower() and "project_type" in known_terms:
            return []
        if "require" in goal.lower() or "missing" in goal.lower():
            return self.generator.generate_questions(task, list(known_terms))
        return []

    def generate_question(self, task: Dict[str, Any], category: str = "missing_requirement") -> InquiryQuestion:
        question = InquiryQuestion(
            task_id=str(task.get("task_id") or "unknown-task"),
            question=f"What is needed to continue the task safely?",
            purpose="Identify the missing information required to complete the task.",
            category=QuestionCategory(category) if category in QuestionCategory._value2member_map_ else QuestionCategory.missing_requirement,
            priority=QuestionPriority.required,
            source="self_generated",
        )
        self.manager.add_question(question.task_id, question)
        return question

    def resolve_question(self, task_id: str, question_id: str, answer: Optional[str], confidence: float = 0.0) -> Optional[InquiryQuestion]:
        return self.manager.resolve_question(task_id, question_id, answer, confidence)

    def get_active_questions(self, task_id: Optional[str] = None) -> List[InquiryQuestion]:
        if task_id is not None:
            return [question for question in self.manager.get_active_questions(task_id) if question.status != "resolved"]
        questions: List[InquiryQuestion] = []
        for current_questions in self.manager._questions.values():
            questions.extend(question for question in current_questions if question.status != "resolved")
        return questions

    def should_wait_for_prerequisites(self, question: InquiryQuestion, resolved_prereqs: Dict[str, bool]) -> bool:
        if not question.dependencies:
            return False
        return any(resolved_prereqs.get(dep, False) is False for dep in question.dependencies)

    def request_user_decision(self, task_id: str, question: str, options: Optional[List[str]] = None, category: str = "feature_decision") -> InquiryQuestion:
        inquiry = InquiryQuestion(
            task_id=task_id,
            question=question,
            purpose="The task requires a user decision before continuing safely.",
            category=QuestionCategory(category) if category in QuestionCategory._value2member_map_ else QuestionCategory.feature_decision,
            priority=QuestionPriority.high,
            source="self_generated",
            requires_user=True,
            options=options or [],
        )
        self.manager.add_question(task_id, inquiry)
        return inquiry

    def check_limits(self, task_id: str, question_count: int) -> bool:
        return self.limits.check_limits(task_id, question_count)

    def resume_after_answer(self, task_id: str, question_id: str, answer: str, confidence: float = 0.9) -> Optional[InquiryQuestion]:
        return self.resolve_question(task_id, question_id, answer, confidence)
