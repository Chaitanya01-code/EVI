from __future__ import annotations

from typing import Any, Dict, Iterable, List

from app.work.events.base import EventSource, SourceRegistry
from app.work.events.normalizer import normalize_event
from app.work.events.repository import WorkEventRepository


class EventCollector:
    def __init__(self, registry: SourceRegistry | None = None, repository: WorkEventRepository | None = None) -> None:
        self.registry = registry or SourceRegistry()
        self.repository = repository or WorkEventRepository()

    def register(self, source: EventSource) -> None:
        self.registry.register(source)

    def collect(self) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        for source_name in self.registry.list():
            source = self.registry.get(source_name)
            for raw in source.collect():
                normalized = normalize_event(source.sanitize_event(raw))
                self.repository.save_event(normalized)
                collected.append(normalized.model_dump(mode="json"))
        return collected

    def ingest(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        normalized = normalize_event(raw_event)
        self.repository.save_event(normalized)
        return normalized.model_dump(mode="json")
