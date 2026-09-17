from app.phase3.inquiry.inquiry_engine import InquiryEngine
from app.phase3.orchestration.inquiry_coordinator import InquiryCoordinator


def test_inquiry_coordinator_starts_and_returns_questions():
    coordinator = InquiryCoordinator()
    task = {"task_id": "task-9", "goal": "Build a RAG application", "state": {"project": "demo"}}
    questions = coordinator.start(task)
    assert questions
    assert coordinator.get_required_information(task)


def test_inquiry_engine_resume_after_answer_updates_state():
    engine = InquiryEngine()
    question = engine.generate_question({"task_id": "task-10"})
    resolved = engine.resume_after_answer("task-10", question.question_id, "Use PostgreSQL + pgvector", confidence=0.92)
    assert resolved is not None
    assert resolved.answer == "Use PostgreSQL + pgvector"
