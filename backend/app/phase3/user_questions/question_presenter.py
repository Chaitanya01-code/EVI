from __future__ import annotations

from typing import List, Optional

from app.phase3.user_questions.models import UserQuestion, UserQuestionStatus


class QuestionPresenter:
    def present(self, task_id: str, question: str, options: Optional[List[str]] = None) -> UserQuestion:
        return UserQuestion(
            question_id=f"uq_{task_id}",
            task_id=task_id,
            message=question,
            options=options or [],
            status=UserQuestionStatus.pending,
        )

    def format_user_message(self, question: str, options: Optional[List[str]] = None) -> str:
        if not options:
            return question
        return f"NOVA needs one decision before continuing:\n{question}\nOptions: {', '.join(options)}"
