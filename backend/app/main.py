from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os

from app.api.chat import chat_router
from app.database.connection import close_pool
from app.database.store import initialize_database_async
from app.phase3.inquiry.inquiry_engine import InquiryEngine
from app.phase4.computer.controller import DesktopAutomationController
from app.phase4.computer.control_indicator import ControlIndicator
from app.phase4.computer.kill_switch import kill_switch
from app.safety.executor_gate import (
    get_kill_switch_status,
    guarded_execute,
    resolve_approval,
    set_kill_switch,
)
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
_control_indicator = ControlIndicator(kill_switch.stop)
kill_switch.set_indicator(_control_indicator.show, _control_indicator.hide)


class ApprovalRequest(BaseModel):
    approve: bool


class KillSwitchRequest(BaseModel):
    enabled: bool


@app.post("/api/approvals/{approval_id}")
async def submit_approval(approval_id: str, payload: ApprovalRequest):
    result = await resolve_approval(approval_id, payload.approve)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Approval was not found.")
    if result["status"] == "expired":
        raise HTTPException(status_code=410, detail="Approval has expired.")
    return result


@app.get("/api/kill-switch")
def get_action_kill_switch():
    return get_kill_switch_status()


@app.post("/api/kill-switch")
def update_action_kill_switch(payload: KillSwitchRequest):
    return set_kill_switch(payload.enabled)


@app.get("/api/computer/control/status")
def computer_control_status():
    return kill_switch.status()


@app.post("/api/computer/control/enable")
def computer_control_enable():
    status = kill_switch.enable()
    if not status["enabled"]:
        raise HTTPException(status_code=503, detail=status)
    return status


@app.post("/api/computer/control/stop")
def computer_control_stop():
    return kill_switch.stop("Computer control was stopped by the user.")


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
async def computer_inspect(payload: dict):
    app_name = str(payload.get("application") or "Notepad")
    result = await guarded_execute(
        {"tool": "computer.inspect_window", "params": {"application": app_name}},
        "computer_api",
        lambda: _computer_controller.inspect_window(app_name),
    )
    return result.get("result") if result["status"] == "ok" else result


@app.post("/api/computer/interact")
async def computer_interact(payload: dict):
    action = str(payload.get("action") or "click")
    app_name = str(payload.get("application") or "Notepad")
    target = str(payload.get("target") or "main")
    if action == "type":
        params = {"application": app_name, "target": target, "text": str(payload.get("text") or "")}
        run = lambda: _computer_controller.type_text(app_name, target, params["text"])
        tool = "computer.type_text"
    else:
        params = {"application": app_name, "target": target}
        run = lambda: _computer_controller.click(app_name, target)
        tool = "computer.click"
    result = await guarded_execute({"tool": tool, "params": params}, "computer_api", run)
    return result.get("result") if result["status"] == "ok" else result


@app.on_event("startup")
async def startup_database():
    if not kill_switch.start_listener():
        logging.getLogger(__name__).error(
            "Computer control remains disabled: %s",
            kill_switch.status()["reason"],
        )
    try:
        await initialize_database_async()
    except Exception:
        logging.getLogger(__name__).exception("PostgreSQL initialization failed")
        raise


@app.on_event("shutdown")
async def shutdown_database():
    kill_switch.shutdown()
    close_pool()

@app.get("/")
def read_root():
    return {"hello from evi"}