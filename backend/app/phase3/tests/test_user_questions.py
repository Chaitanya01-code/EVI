from app.phase3.user_questions.question_presenter import QuestionPresenter


def test_question_presenter_formats_user_decision_prompt():
    presenter = QuestionPresenter()
    text = presenter.format_user_message(
        "Should this RAG deployment use PostgreSQL + pgvector?",
        ["PostgreSQL + pgvector", "Dedicated vector database"],
    )
    assert "NOVA needs one decision" in text
    assert "PostgreSQL + pgvector" in text
