from app.phase3.inquiry.inquiry_engine import InquiryEngine
from app.phase3.inquiry.models import InquiryQuestion, QuestionCategory, QuestionPriority


def test_question_generated_when_required_information_missing():
    engine = InquiryEngine()
    task = {"task_id": "task-1", "goal": "Build a RAG application", "state": {"project": "demo"}}
    questions = engine.get_required_information(task)
    assert questions
    assert any("documents" in (q.question.lower()) or "retrieval" in (q.question.lower()) for q in questions)


def test_question_not_generated_when_information_known():
    engine = InquiryEngine()
    task = {
        "task_id": "task-2",
        "goal": "Build a RAG app",
        "state": {"project": "demo", "project_type": "rag", "vector_store": "pgvector"},
    }
    questions = engine.get_required_information(task)
    assert not questions


def test_user_decision_requested_for_high_impact_choice():
    engine = InquiryEngine()
    result = engine.request_user_decision(
        task_id="task-3",
        question="Should this system use PostgreSQL + pgvector or a dedicated vector database?",
        options=["PostgreSQL + pgvector", "Dedicated vector database"],
    )
    assert result.requires_user is True
    assert result.options


def test_dependent_questions_are_waited_on():
    engine = InquiryEngine()
    q1 = InquiryQuestion(question_id="q1", task_id="task-4", question="Which deployment platform should be used?", category=QuestionCategory.project_information, priority=QuestionPriority.critical, purpose="The deployment target is required before building the config.", source="self_generated")
    q2 = InquiryQuestion(question_id="q2", task_id="task-4", question="Which cloud config should be created?", category=QuestionCategory.environment_information, priority=QuestionPriority.high, purpose="Configuration depends on the platform choice.", source="self_generated", dependencies=["q1"])

    assert engine.should_wait_for_prerequisites(q2, {"q1": True}) is False
    assert engine.should_wait_for_prerequisites(q2, {"q1": False}) is True


def test_inquiry_limits_prevent_infinite_question_loops():
    engine = InquiryEngine(max_questions_per_task=2, max_research_attempts_per_question=1)
    assert engine.check_limits(task_id="task-5", question_count=2) is False
    assert engine.check_limits(task_id="task-5", question_count=3) is True
