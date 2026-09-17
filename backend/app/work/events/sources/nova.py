from __future__ import annotations

from typing import Any, Dict, Iterable, List

from app.work.events.base import EventSource


class NovaEventSource(EventSource):
    name = "nova"

    def collect(self) -> Iterable[Dict[str, Any]]:
        return []
