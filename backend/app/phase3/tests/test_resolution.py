from app.phase3.resolution.answer_resolver import AnswerResolver


def test_question_resolution_uses_project_state_when_available():
    result = AnswerResolver().resolve(
        "What vector database should be used?",
        context={"current_work_state": {"project": "demo", "vector_store": "pgvector"}},
    )
    assert result.answer is not None
    assert result.confidence >= 0.8
