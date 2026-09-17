from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.work.context.context_engine import ContextEngine
from app.work.context.models import ContextSnapshot
from app.work.events.repository import WorkEventRepository


@dataclass
class CurrentWorkStateService:
    repository: WorkEventRepository = None
    engine: ContextEngine = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = WorkEventRepository()
        if self.engine is None:
            self.engine = ContextEngine()

    def get_current_state(self, project_name: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        events = self.repository.list_recent(project_name=project_name, limit=100)
        state = self.engine.build_state(events)
        return {
            "project": state.project,
            "workspace": state.workspace,
            "application": state.application,
            "current_file": state.current_file,
            "branch": state.branch,
            "current_task": state.current_task,
            "current_goal": state.current_goal,
            "current_problem": state.current_problem,
            "recent_actions": state.recent_actions,
            "confidence": state.confidence,
            "updated_at": state.updated_at.isoformat(),
        }

    def snapshot(self, project_name: Optional[str] = None) -> ContextSnapshot:
        events = self.repository.list_recent(project_name=project_name, limit=100)
        state = self.engine.build_state(events)
        return ContextSnapshot(
            current_work=state,
            recent_events=events,
            project_context={"project": project_name or state.project},
            active_task={"task": state.current_task, "goal": state.current_goal},
        )


current_work_state_service = CurrentWorkStateService()
