from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List


class EventSource(ABC):
    name: str = "base"

    @abstractmethod
    def collect(self) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError

    @staticmethod
    def sanitize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
        return {**raw}


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: Dict[str, EventSource] = {}

    def register(self, source: EventSource) -> None:
        self._sources[source.name] = source

    def list(self) -> List[str]:
        return sorted(self._sources)

    def get(self, name: str) -> EventSource:
        return self._sources[name]
