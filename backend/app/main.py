from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.api.chat import chat_router
from app.database.connection import close_pool
from app.database.store import initialize_database_async
from app.phase3.inquiry.inquiry_engine import InquiryEngine
from app.phase4.computer.controller import DesktopAutomationController
from app.voice.speech_to_text import stt_router
from app.api.routes.lab import lab_router
from app.work.api import work_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("EVI_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stt_router, prefix="/api/voice")
app.include_router(chat_router, prefix="/api")
app.include_router(lab_router, prefix="/api")
app.include_router(work_router, prefix="/api")

_inquiry_engine = InquiryEngine()
_computer_controller = DesktopAutomationController()


@app.get("/api/inquiry/status")
def inquiry_status():
    active_questions = _inquiry_engine.get_active_questions()
    return {"status": "ready", "active": bool(active_questions), "active_questions": len(active_questions), "max_questions": _inquiry_engine.limits.max_questions_per_task}


@app.post("/api/inquiry/start")
def inquiry_start(payload: dict):
    questions = _inquiry_engine.start(payload)
    from app.api.lab_events import lab_event_bus

    lab_event_bus.publish({"event": "inquiry_started", "task_id": str(payload.get("task_id") or "unknown-task"), "question_count": len(questions)})
    for question in questions:
        lab_event_bus.publish({"event": "question_generated", "task_id": question.task_id, "question_id": question.question_id, "category": question.category.value})
    return {"status": "started", "questions": [q.model_dump(mode="json") for q in questions]}


@app.get("/api/inquiry/questions")
def inquiry_questions():
    return {"questions": [q.model_dump(mode="json") for q in _inquiry_engine.get_active_questions()]}


@app.post("/api/inquiry/{question_id}/answer")
def inquiry_answer(question_id: str, payload: dict):
    from app.api.lab_events import lab_event_bus

    task_id = str(payload.get("task_id") or "unknown-task")
    resolved = _inquiry_engine.resolve_question(
        task_id,
        question_id,
        payload.get("answer"),
        float(payload.get("confidence", 0.0) or 0.0),
    )
    if resolved is None:
        return {"status": "accepted", "question_id": question_id, "message": "Answer recorded."}
    lab_event_bus.publish({"event": "decision_resolved", "task_id": task_id, "question_id": question_id})
    return {"status": "resolved", "question_id": question_id, "answer": resolved.answer, "confidence": resolved.confidence}


@app.get("/api/computer/applications")
def computer_applications():
    return {"applications": ["Notepad", "Calculator", "Microsoft Edge", "Google Chrome", "Visual Studio Code"]}


@app.post("/api/computer/inspect")
def computer_inspect(payload: dict):
    app_name = str(payload.get("application") or "Notepad")
    return _computer_controller.inspect_window(app_name)


@app.post("/api/computer/interact")
def computer_interact(payload: dict):
    action = str(payload.get("action") or "click")
    app_name = str(payload.get("application") or "Notepad")
    target = str(payload.get("target") or "main")
    if action == "type":
        return _computer_controller.type_text(app_name, target, str(payload.get("text") or ""))
    return _computer_controller.click(app_name, target)


@app.on_event("startup")
async def startup_database():
    try:
        await initialize_database_async()
    except Exception:
        logging.getLogger(__name__).exception("PostgreSQL initialization failed")
        raise


@app.on_event("shutdown")
async def shutdown_database():
    close_pool()

@app.get("/")
def read_root():
    return {"hello from evi"}