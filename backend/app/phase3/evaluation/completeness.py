from __future__ import annotations

from typing import Any, Dict, Optional


class CompletenessChecker:
    def evaluate(self, question: str, answer: Optional[str]) -> Dict[str, Any]:
        if not answer:
            return {"complete": False, "confidence": 0.0, "reason": "No answer available."}
        text = (answer or "").strip()
        return {
            "complete": bool(text),
            "confidence": 0.7 if len(text) > 20 else 0.5,
            "reason": "Answer exists and is non-empty.",
        }
