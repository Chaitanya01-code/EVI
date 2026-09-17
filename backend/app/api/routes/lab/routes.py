from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agents.desktop.registry import desktop_tools
from app.agents.browser.registry import browser_tools
from app.agents.coding.registry import coding_tools
from app.agents.cloud.registry import cloud_tools
from app.api.lab_events import lab_event_bus
from app.api.lab_schemas import HealthResponse, PageResponse
from app.database.connection import get_connection
from app.database import lab_store
from app.task.task_router import build_default_registry
from app.llm.router import llm_router
from app.phase3.inquiry.inquiry_engine import InquiryEngine
from app.phase4.computer.controller import DesktopAutomationController
from app.work.context.service import current_work_state_service

lab_router = APIRouter(prefix="/lab", tags=["EVI Lab"])
_inquiry_engine = InquiryEngine()
_computer_controller = DesktopAutomationController()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _page(data: list, total: int, limit: int, offset: int) -> Dict[str, Any]:
    return {"data": data, "pagination": {"limit": limit, "offset": offset, "total": total}, "timestamp": _now()}


def _safe_task(task: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in task.items() if key != "user_id"}


def _db_call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Lab data is temporarily unavailable.") from error


def _agent_data(agent_id: str) -> Optional[Dict[str, Any]]:
    registry = build_default_registry()
    agent = next((item for key, item in registry._agents.items() if key.value == agent_id), None)
    if agent is None:
        return None
    tools = []
    tool_registry = getattr(agent, "tools", None)
    if tool_registry and hasattr(tool_registry, "list_tools"):
        tools = tool_registry.list_tools()
    registry_by_agent = {"desktop": desktop_tools, "browser": browser_tools, "coding": coding_tools, "cloud": cloud_tools}
    if agent_id in registry_by_agent:
        tools = registry_by_agent[agent_id].list_tools()
    activities, _ = _db_call(lab_store.list_tasks, 5, 0, {"agent_type": agent_id})
    last_activity = activities[0].get("timestamp") if activities else None
    return {"id": agent_id, "name": agent.__class__.__name__, "status": "idle", "available": True, "capabilities": tools, "last_activity": last_activity, "current_task": None, "recent_executions": activities}


@lab_router.get("/overview", summary="Get the EVI Lab overview", response_model=Dict[str, Any])
def overview() -> Dict[str, Any]:
    counts = _db_call(lab_store.overview_counts)
    agents = build_default_registry().names()
    return {"timestamp": _now(), "system": {"status": "healthy"}, "agents": {"total": len(agents), "active": counts["running_tasks"], "idle": max(0, len(agents) - counts["running_tasks"])}, "tasks": {"running": counts["running_tasks"], "completed": counts["completed_tasks"], "failed": counts["failed_tasks"]}, "conversations": {"total": counts["conversations"]}, "memory": {"total": counts["memories"]}}


@lab_router.get("/agents", summary="List registered agents", response_model=Dict[str, Any])
def agents() -> Dict[str, Any]:
    registry = build_default_registry()
    result = []
    for agent_id in registry.names():
        item = _agent_data(agent_id)
        if item:
            item["recent_executions"] = [_safe_task(task) for task in item["recent_executions"]]
            result.append(item)
    return {"data": result, "timestamp": _now()}


@lab_router.get("/agents/{agent_id}", summary="Get agent details", response_model=Dict[str, Any])
def agent_detail(agent_id: str) -> Dict[str, Any]:
    result = _agent_data(agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    result["recent_executions"] = [_safe_task(task) for task in result["recent_executions"]]
    return {"data": result, "timestamp": _now()}


@lab_router.get("/agents/{agent_id}/activity", summary="Get agent activity", response_model=PageResponse)
def agent_activity(agent_id: str, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    if _agent_data(agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    data, total = _db_call(lab_store.list_tasks, limit, offset, {"agent_type": agent_id})
    return _page([_safe_task(item) for item in data], total, limit, offset)


@lab_router.get("/tasks", summary="List task history", response_model=PageResponse)
def tasks(status: Optional[str] = None, agent: Optional[str] = None, task_type: Optional[str] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    data, total = _db_call(lab_store.list_tasks, limit, offset, {"status": status, "agent_type": agent, "task_type": task_type, "date_from": date_from, "date_to": date_to})
    return _page([_safe_task(item) for item in data], total, limit, offset)


@lab_router.get("/tasks/{task_id}", summary="Get task detail", response_model=Dict[str, Any])
def task_detail(task_id: str) -> Dict[str, Any]:
    task = _db_call(lab_store.get_task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task["steps"] = _db_call(lab_store.list_steps, task_id)
    return {"data": _safe_task(task), "timestamp": _now()}


@lab_router.get("/tasks/{task_id}/steps", summary="Get task steps", response_model=PageResponse)
def task_steps(task_id: str, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    if _db_call(lab_store.get_task, task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    all_steps = _db_call(lab_store.list_steps, task_id)
    return _page(all_steps[offset:offset + limit], len(all_steps), limit, offset)


@lab_router.get("/conversations", summary="List conversation summaries", response_model=PageResponse)
def conversations(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    data, total = _db_call(lab_store.list_conversations, limit, offset)
    return _page([_safe_task(item) for item in data], total, limit, offset)


@lab_router.get("/conversations/{conversation_id}", summary="Get conversation messages", response_model=PageResponse)
def conversation_detail(conversation_id: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    data, total = _db_call(lab_store.conversation_messages, conversation_id, limit, offset)
    if not data and offset == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _page([{key: value for key, value in item.items() if key != "user_id"} for item in data], total, limit, offset)


@lab_router.get("/memory", summary="List safe memories", response_model=PageResponse)
def memory(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    data, total = _db_call(lab_store.list_memories, limit, offset)
    return _page(data, total, limit, offset)


@lab_router.get("/executions", summary="List tool executions", response_model=PageResponse)
def executions(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    data, total = _db_call(lab_store.list_executions, limit, offset)
    return _page([_safe_task(item) for item in data], total, limit, offset)


@lab_router.get("/capabilities", summary="List registered EVI capabilities", response_model=Dict[str, Any])
def capabilities() -> Dict[str, Any]:
    registry = build_default_registry()
    tool_registries = {"desktop": desktop_tools, "browser": browser_tools, "coding": coding_tools, "cloud": cloud_tools}
    agents = []
    tools = []
    for agent_id in registry.names():
        agent_tools = tool_registries.get(agent_id)
        names = agent_tools.list_tools() if agent_tools and hasattr(agent_tools, "list_tools") else []
        agents.append({"id": agent_id, "name": registry.names()[agent_id], "tools": names})
        tools.extend({"agent": agent_id, "name": name} for name in names)
    return {
        "agents": agents,
        "tools": tools,
        "features": ["text_chat", "task_history", "inquiry", "memory", "live_events"],
        "voice": bool(os.getenv("DEEPGRAM_API_KEY")),
        "browser": "browser" in registry.names(),
        "desktop": "desktop" in registry.names(),
        "coding": "coding" in registry.names(),
        "research": "browser" in registry.names(),
        "memory": True,
        "live_events": True,
        "timestamp": _now(),
    }


def _safe_call(function, fallback):
    try:
        return function()
    except Exception:
        return fallback


@lab_router.get("/observability", summary="Get real EVI Lab observability data", response_model=Dict[str, Any])
def observability() -> Dict[str, Any]:
    registry = build_default_registry()
    names = registry.names()
    tool_registries = {"desktop": desktop_tools, "browser": browser_tools, "coding": coding_tools, "cloud": cloud_tools}
    tools = []
    for agent_id, agent_name in names.items():
        for tool_name in tool_registries.get(agent_id, []).list_tools() if agent_id in tool_registries else []:
            tools.append({"name": tool_name, "agent": agent_name, "category": tool_name.split(".")[0], "status": "available"})

    tasks, _ = _db_call(lab_store.list_tasks, 50, 0, {})
    executions, _ = _db_call(lab_store.list_executions, 100, 0)
    health_data = health()
    llm_data = llm_status()
    questions = [question.model_dump(mode="json") for question_list in _inquiry_engine.manager._questions.values() for question in question_list]
    active_questions = [question for question in questions if question.get("status") != "resolved"]
    failed_tasks = [task for task in tasks if task.get("status") == "failed" or task.get("success") is False]
    today = _now().date()
    tasks_today = [task for task in tasks if getattr(task.get("timestamp"), "date", lambda: None)() == today]
    agent_data = []
    for agent_id in names:
        item = _agent_data(agent_id)
        if item:
            item["recent_executions"] = [_safe_task(task) for task in item["recent_executions"]]
            agent_data.append(item)

    return {
        "overview": overview(),
        "tasks": [_safe_task(task) for task in tasks],
        "traces": [{"task_id": task.get("task_id"), "request": task.get("original_text"), "status": task.get("status"), "agent": task.get("agent"), "action": task.get("action"), "verified": task.get("verified"), "steps": _db_call(lab_store.list_steps, task.get("task_id"))} for task in tasks[:20]],
        "executions": executions,
        "events": lab_event_bus.recent(),
        "work_context": _safe_call(current_work_state_service.get_current_state, {}),
        "applications": [{"name": name, "available": True, "status": "discoverable"} for name in _computer_controller.applications],
        "desktop": {"status": "available", "applications": _computer_controller.applications, "inspection": "Use the desktop inspection endpoint for a selected application."},
        "agents": agent_data,
        "tools": tools,
        "inquiry": {"active": active_questions, "all": questions, "max_questions": _inquiry_engine.limits.max_questions_per_task},
        "research": {"status": "not_available", "message": "No research result store is connected to the Lab."},
        "memory": _safe_call(lambda: {"data": lab_store.list_memories(50, 0)[0]}, {"data": []}),
        "decisions": [question for question in questions if question.get("requires_user")],
        "projects": {"status": "not_available", "message": "No project registry is connected to the Lab."},
        "verification": [execution for execution in executions if execution.get("verified") is not None],
        "errors": [{"timestamp": task.get("timestamp"), "task_id": task.get("task_id"), "agent": task.get("agent"), "message": task.get("error") or task.get("message"), "status": task.get("status")} for task in failed_tasks],
        "performance": {"tasks_today": len(tasks_today), "completed": sum(task.get("status") == "completed" for task in tasks), "failed": len(failed_tasks), "active": sum(task.get("status") in {"executing", "verifying", "planning"} for task in tasks)},
        "models": llm_data,
        "security": {"status": "active", "confirmation_required": [task for task in tasks if task.get("status") == "awaiting_permission"], "policy": "Protected actions require confirmation."},
        "integrations": health_data.get("components", {}),
        "health": health_data,
        "llm": llm_data,
        "timestamp": _now(),
    }


@lab_router.get("/system/health", summary="Check EVI component health", response_model=HealthResponse)
def health() -> Dict[str, Any]:
    components = {"api": "healthy", "agent_registry": "healthy", "orchestrator": "healthy", "llm": "configured" if os.getenv("GEMINI_API_KEY") else "unconfigured", "stt": "configured" if os.getenv("DEEPGRAM_API_KEY") else "unconfigured"}
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1")
        components["database"] = "healthy"
    except Exception:
        components["database"] = "unavailable"
    try:
        import pyttsx3  # noqa: F401
        components["tts"] = "available"
    except Exception:
        components["tts"] = "unavailable"
    status = "healthy" if components["database"] == "healthy" else "degraded"
    return {"status": status, "timestamp": _now(), "components": components}


@lab_router.get("/llm/status", summary="Get safe LLM fallback status", response_model=Dict[str, Any])
def llm_status() -> Dict[str, Any]:
    active = llm_router.last_response
    return {
        "primary": {"provider": "gemini", "model": llm_router.models()[0].model},
        "active_model": active.model if active else None,
        "provider": active.provider if active else None,
        "fallback_used": active.fallback_used if active else False,
        "last_latency_ms": active.latency_ms if active else None,
        "models": [status.__dict__ for status in llm_router.statuses.values()],
        "timestamp": _now(),
    }


@lab_router.get("/events", summary="Stream safe Lab events")
async def events() -> StreamingResponse:
    async def stream():
        async for event in lab_event_bus.subscribe():
            yield f"event: {event.get('event', 'update')}\ndata: {json.dumps(event, default=str)}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
