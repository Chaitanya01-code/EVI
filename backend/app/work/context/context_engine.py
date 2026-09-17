from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.work.context.confidence import ConfidenceTracker
from app.work.context.event_window import EventWindow
from app.work.context.inference import infer_intent
from app.work.context.models import CurrentWorkState
from app.work.events.normalizer import normalize_event


class ContextEngine:
    def __init__(self, event_window: Optional[EventWindow] = None) -> None:
        self.event_window = event_window or EventWindow()
        self.confidence = ConfidenceTracker()

    def _deduplicate(self, events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        for event in events:
            item = dict(event)
            event_id = item.get("event_id") or item.get("source") + str(item.get("timestamp")) + str(item.get("event_type")) + str(item.get("file_path") or item.get("command") or "")
            deduped[event_id] = item
        return list(deduped.values())

    def build_state(self, events: Iterable[Dict[str, Any]]) -> CurrentWorkState:
        ordered = self._deduplicate(events)
        windowed = self.event_window.filter([
            normalize_event(event).model_dump(mode="json")
            for event in ordered
        ])

        project = None
        workspace = None
        application = None
        current_file = None
        branch = None
        current_problem = None
        recent_actions: List[str] = []

        for event in windowed:
            event_type = event.get("event_type")
            project = project or event.get("project_name")
            workspace = workspace or event.get("workspace_path")
            application = application or event.get("application")
            if event.get("file_path"):
                current_file = event.get("file_path")
            if event.get("branch"):
                branch = event.get("branch")
            if event_type == "command_executed" and event.get("exit_code") not in (0, None):
                current_problem = f"Command failed: {event.get('command', 'command')} (exit {event.get('exit_code')})"
                recent_actions.append("ran a failing command")
            elif event_type == "file_modified":
                recent_actions.append("edited code")
            elif event_type == "git_branch_changed":
                recent_actions.append("changed branch")
            elif event_type == "application_opened":
                recent_actions.append(f"opened {event.get('application') or 'application'}")

        if current_problem is None and any(item.get("event_type") == "command_executed" and item.get("exit_code") not in (0, None) for item in windowed):
            failed_command = next(item for item in windowed if item.get("event_type") == "command_executed" and item.get("exit_code") not in (0, None))
            current_problem = f"{failed_command.get('command', 'Command')} failed with exit code {failed_command.get('exit_code')}"

        inferred_intent = infer_intent(windowed)
        if inferred_intent:
            current_problem = current_problem or f"Likely current intent: {inferred_intent}"

        confidence = {
            "project": 0.98 if project else 0.0,
            "application": 0.99 if application else 0.0,
            "task": 0.8 if current_file else 0.0,
            "goal": 0.65 if current_problem else 0.0,
        }

        return CurrentWorkState(
            project=project,
            workspace=workspace,
            application=application,
            current_file=current_file,
            branch=branch,
            current_task=inferred_intent,
            current_goal=current_problem,
            current_problem=current_problem,
            recent_actions=recent_actions[-10:],
            completed_steps=[],
            pending_decisions=[],
            possible_next_actions=[],
            relevant_research=[],
            confidence=confidence,
            updated_at=datetime.now(timezone.utc),
        )
