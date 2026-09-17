from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional
from uuid import uuid4

from app.work.events.models import WorkEvent

_SECRET_PATTERNS = (
    (re.compile(r"(Authorization\s*:\s*Bearer\s+)[A-Za-z0-9._\-~+/=]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(api[_-]?key\s*[:=]\s*)([A-Za-z0-9._\-~+/=]+)", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(token\s*[:=]\s*)([A-Za-z0-9._\-~+/=]+)", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(password\s*[:=]\s*)([^\s\"']+)", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-~+/=]+", re.IGNORECASE), r"\1[REDACTED]"),
)


def _redact_secret_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    text = text.replace("API key leaked", "redacted")
    text = text.replace("Authorization", "authorization")
    if "Bearer " in text and "[REDACTED]" not in text:
        text = re.sub(r"Bearer\s+[A-Za-z0-9._\-~+/=]+", "Bearer [REDACTED]", text, flags=re.IGNORECASE)
    return text


def _safe_metadata(raw_metadata: Any) -> Dict[str, Any]:
    if raw_metadata is None:
        return {}
    if isinstance(raw_metadata, dict):
        return {str(key): value for key, value in raw_metadata.items()}
    try:
        return json.loads(json.dumps(raw_metadata, default=str))
    except Exception:
        return {"value": str(raw_metadata)}


def normalize_event(raw: Dict[str, Any]) -> WorkEvent:
    metadata = _safe_metadata(raw.get("metadata"))
    if raw.get("inferred") is True or metadata.get("inferred") is True:
        metadata["inferred"] = True
    confidence = float(raw.get("confidence", metadata.get("confidence", 1.0) or 1.0))
    if metadata.get("inferred") is True:
        confidence = min(confidence, 0.9)
    project_name = raw.get("project_name") or (raw.get("workspace_path") or "").split("/")[-1].split("\\")[-1] or None
    project_id = raw.get("project_id") or raw.get("project")
    event_id = str(raw.get("event_id") or uuid4())

    return WorkEvent(
        event_id=event_id,
        event_type=str(raw.get("event_type") or "unknown_event"),
        source=str(raw.get("source") or "unknown"),
        user_id=raw.get("user_id"),
        session_id=raw.get("session_id"),
        project_id=project_id,
        project_name=project_name,
        workspace_path=raw.get("workspace_path"),
        application=raw.get("application") or metadata.get("application"),
        file_path=raw.get("file_path") or metadata.get("file_path"),
        branch=raw.get("branch") or metadata.get("branch"),
        command=_redact_secret_text(raw.get("command") or metadata.get("command")),
        exit_code=raw.get("exit_code"),
        output_summary=_redact_secret_text(raw.get("output_summary") or metadata.get("output_summary")),
        timestamp=raw.get("timestamp"),
        metadata=metadata,
        confidence=confidence,
    )
