from app.phase3.inquiry.inquiry_engine import InquiryEngine


def test_question_generation_for_missing_rag_requirements():
    engine = InquiryEngine()
    task = {"task_id": "task-rag", "goal": "Build a RAG application"}
    questions = engine.get_required_information(task)
    assert questions
    assert any("documents" in q.question.lower() or "retrieval" in q.question.lower() for q in questions)
