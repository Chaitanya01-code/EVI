from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from app.training.redact import redact


logger = logging.getLogger(__name__)
TRAINING_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "training"


def is_training_logging_enabled() -> bool:
    value = os.getenv("EVI_LOG_TRAINING_DATA", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _redact_values(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {key: _redact_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_values(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_values(item) for item in value]
    return value


def log_intent(
    user_text: str,
    context_summary: Any,
    source: str,
    classifier_used: str,
    predicted: dict[str, Any],
    latency_ms: float,
    error: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Append one redacted classifier record; logging errors are reported, never raised."""
    if not is_training_logging_enabled():
        return None

    timestamp = datetime.now(timezone.utc)
    try:
        summary = context_summary if isinstance(context_summary, str) else json.dumps(
            context_summary or {}, ensure_ascii=False, default=str
        )
        record = {
            "id": str(uuid4()),
            "ts": timestamp.isoformat(),
            "source": source,
            "user_text": redact(user_text),
            "context_summary": redact(summary)[:1500],
            "classifier_used": classifier_used,
            "predicted": _redact_values(predicted),
            "latency_ms": latency_ms,
            "error": redact(error) if error is not None else None,
            "feedback": None,
            "outcome": None,
        }
        path = TRAINING_DATA_DIR / f"intent_log_{timestamp.date().isoformat()}.jsonl"
        TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        return record
    except Exception:
        logger.warning("Unable to append intent training record", exc_info=True)
        return None
