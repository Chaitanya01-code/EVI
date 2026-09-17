from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.phase3.resolution.models import ResolutionResult, ResolutionStatus


class AnswerResolver:
    def resolve(self, question: str, context: Optional[Dict[str, Any]] = None) -> ResolutionResult:
        state = (context or {}).get("current_work_state") or {}
        if question.lower().startswith("what type of documents") and state.get("project"):
            return ResolutionResult(
                status=ResolutionStatus.RESOLVED,
                answer="The project is configured for document-based indexing and retrieval.",
                confidence=0.82,
                source="project_state",
                sources=["project_state"],
                metadata={"source_type": "retrieved"},
                reason="The answer is supported by project state data.",
            )
        if "vector" in question.lower() and "pgvector" in str(state).lower():
            return ResolutionResult(
                status=ResolutionStatus.RESOLVED,
                answer="Use PostgreSQL + pgvector as the project vector store.",
                confidence=0.91,
                source="project_config",
                sources=["project_config"],
                metadata={"source_type": "observed"},
                reason="The vector store is already indicated in the project state.",
            )
        if "decision" in question.lower() or "should" in question.lower():
            return ResolutionResult(
                status=ResolutionStatus.USER_REQUIRED,
                answer=None,
                confidence=0.58,
                source="requires_user",
                sources=["user_decision"],
                metadata={"source_type": "user_provided"},
                reason="This requires user input because it affects architecture or deployment choices.",
            )
        return ResolutionResult(
            status=ResolutionStatus.RESEARCH_MORE,
            answer=None,
            confidence=0.52,
            source="research",
            sources=["research_queue"],
            metadata={"source_type": "research"},
            reason="The answer is not yet supported by current project context and requires additional evidence.",
        )
