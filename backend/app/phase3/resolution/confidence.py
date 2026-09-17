from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceThresholds:
    strong_observed: float = 0.95
    strong_researched: float = 0.80
    reasonable_inference: float = 0.60
    uncertain: float = 0.60

    def classify(self, value: float) -> str:
        if value >= self.strong_observed:
            return "strong_observed"
        if value >= self.strong_researched:
            return "strong_researched"
        if value >= self.reasonable_inference:
            return "reasonable_inference"
        return "uncertain"


DEFAULT_CONFIDENCE = ConfidenceThresholds()
