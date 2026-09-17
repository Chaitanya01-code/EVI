from __future__ import annotations

from typing import Dict, Optional


class ConfidenceTracker:
    def __init__(self) -> None:
        self._values: Dict[str, float] = {}

    def set(self, key: str, value: float) -> None:
        self._values[key] = max(0.0, min(1.0, float(value)))

    def get(self, key: str, default: float = 0.0) -> float:
        return self._values.get(key, default)

    def as_dict(self) -> Dict[str, float]:
        return dict(self._values)

    def update_from_observed(self, observed: Optional[dict], key: str) -> None:
        if not observed:
            return
        self.set(key, float(observed.get("confidence", 1.0)))
