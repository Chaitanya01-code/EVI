from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from phase2.decision.engine import evaluate_decision
from phase2.information.resolver import resolve_information
from phase2.proactive.intelligence import ProactiveIntelligence
from app.work.context.service import current_work_state_service
from app.work.events.collector import EventCollector
from app.work.events.normalizer import normalize_event
from app.work.events.repository import WorkEventRepository

work_router = APIRouter(prefix="/work", tags=["Current Work"])
_work_event_collector = EventCollector(repository=WorkEventRepository())


@work_router.get("/context", summary="Get the current work context")
def get_current_context() -> Dict[str, Any]:
    return current_work_state_service.get_current_state()


@work_router.get("/state", summary="Get current work state")
def get_work_state() -> Dict[str, Any]:
    return current_work_state_service.get_current_state()


@work_router.get("/events", summary="Get recent normalized work events")
def get_events(limit: int = Query(20, ge=1, le=100), project: Optional[str] = None) -> Dict[str, Any]:
    repo = WorkEventRepository()
    return {"data": repo.list_recent(project_name=project, limit=limit), "count": limit}


@work_router.post("/events", summary="Ingest a normalized work event")
def ingest_event(event: Dict[str, Any]) -> Dict[str, Any]:
    if "event_type" not in event or "source" not in event:
        raise HTTPException(status_code=422, detail="event_type and source are required")
    normalized = normalize_event(event)
    return _work_event_collector.ingest(normalized.model_dump(mode="json"))


@work_router.post("/decision/evaluate", summary="Evaluate whether a requested action is safe, research-required, or needs approval")
def evaluate_action_decision(payload: Dict[str, Any]) -> Dict[str, Any]:
    question = str(payload.get("question") or "")
    state = payload.get("state") or {}
    context = payload.get("context") or {}
    return evaluate_decision(question, state=state, context=context).model_dump(mode="json")


@work_router.post("/information/resolve", summary="Classify whether information is already known, discoverable, or requires user approval")
def resolve_info(payload: Dict[str, Any]) -> Dict[str, Any]:
    question = str(payload.get("question") or "")
    state = payload.get("state") or {}
    context = payload.get("context") or {}
    return resolve_information(question, state=state, context=context).model_dump(mode="json")


@work_router.post("/proactive/opportunities", summary="List proactive opportunities in the current work state")
def proactive_opportunities(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = payload.get("state") or {}
    return {"data": ProactiveIntelligence().detect(state)}
