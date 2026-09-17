from __future__ import annotations

from typing import Optional

from app.phase3.user_questions.models import UserQuestion, UserQuestionStatus


class AnswerHandler:
    def handle(self, question: UserQuestion, answer: str) -> UserQuestion:
        question.answer = answer
        question.status = UserQuestionStatus.answered
        return question

    def validate(self, answer: str) -> bool:
        return bool(answer and answer.strip())
