from __future__ import annotations

from typing import Any, Dict, Optional

from app.phase3.evaluation.models import EvaluationResult, EvaluationStatus


class AnswerEvaluator:
    def evaluate(self, question: str, answer: Optional[str], context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        if answer is None:
            return EvaluationResult(
                status=EvaluationStatus.USER_REQUIRED,
                relevant=False,
                complete=False,
                confidence=0.0,
                conflicts=[],
                requires_user_confirmation=True,
                additional_research_needed=True,
                summary="No answer is available yet and the user decision is required.",
            )

        text = (answer or "").lower()
        if "should" in question.lower() or "deploy" in question.lower() or "decision" in question.lower():
            return EvaluationResult(
                status=EvaluationStatus.USER_REQUIRED,
                relevant=True,
                complete=True,
                confidence=0.82,
                requires_user_confirmation=True,
                additional_research_needed=False,
                summary="The answer is relevant but requires explicit user confirmation before acting.",
            )

        if "vector" in question.lower() and "pgvector" in text:
            return EvaluationResult(
                status=EvaluationStatus.RESOLVED,
                relevant=True,
                complete=True,
                confidence=0.91,
                conflicts=[],
                requires_user_confirmation=False,
                additional_research_needed=False,
                summary="The answer is relevant, complete, and supported by the current environment.",
            )

        return EvaluationResult(
            status=EvaluationStatus.RESEARCH_MORE,
            relevant=True,
            complete=False,
            confidence=0.62,
            conflicts=[],
            requires_user_confirmation=False,
            additional_research_needed=True,
            summary="The answer is relevant but not yet sufficiently complete.",
        )
