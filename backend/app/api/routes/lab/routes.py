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

lab_router = APIRouter(prefix="/lab", tags=["EVI Lab"])


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
    return _page([], 0, limit, offset)


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


@lab_router.get("/events", summary="Stream safe Lab events")
async def events() -> StreamingResponse:
    async def stream():
        async for event in lab_event_bus.subscribe():
            yield f"event: {event.get('event', 'update')}\ndata: {json.dumps(event, default=str)}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
