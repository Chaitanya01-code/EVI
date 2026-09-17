from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


class EventWindow:
    def __init__(self, max_events: int | None = None, time_window_minutes: int | None = None) -> None:
        self.max_events = max_events if max_events is not None else int(os.getenv("CONTEXT_EVENT_WINDOW", "100"))
        self.time_window_minutes = time_window_minutes if time_window_minutes is not None else int(os.getenv("CONTEXT_TIME_WINDOW_MINUTES", "60"))

    def filter(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not events:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.time_window_minutes)
        filtered = []
        for event in events:
            ts = event.get("timestamp")
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                dt = ts
            if dt is not None and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt is not None and dt >= cutoff:
                filtered.append(event)
        return filtered[-self.max_events:]

    def current_session(self, events: List[Dict[str, Any]], session_id: str | None = None) -> List[Dict[str, Any]]:
        if session_id is None:
            return events
        return [event for event in events if event.get("session_id") == session_id]
