from app.phase3.evaluation.answer_evaluator import AnswerEvaluator


def test_answer_evaluator_marks_user_decision_as_required():
    result = AnswerEvaluator().evaluate(
        "Should this system use PostgreSQL + pgvector or a dedicated vector database?",
        answer=None,
    )
    assert result.requires_user_confirmation is True
    assert result.status.value == "USER_REQUIRED"
