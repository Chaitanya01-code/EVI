from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List


class LabEventBus:
    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue[Dict[str, Any]]] = []
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def publish(self, event: Dict[str, Any]) -> None:
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
        with self._lock:
            self._history.append(payload)
            self._history = self._history[-200:]
            subscribers = list(self._subscribers)
        for queue in subscribers:
            loop = getattr(queue, "_lab_loop", None)
            if loop and loop.is_running():
                loop.call_soon_threadsafe(queue.put_nowait, payload)

    async def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=100)
        queue._lab_loop = asyncio.get_running_loop()
        with self._lock:
            self._subscribers.append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])


lab_event_bus = LabEventBus()
