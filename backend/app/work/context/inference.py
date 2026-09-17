from __future__ import annotations

from typing import Any, Dict, Optional


def infer_intent(events: list[dict[str, Any]]) -> Optional[str]:
    if not events:
        return None
    recent = events[-10:]
    if any(e.get("event_type") == "command_executed" and (e.get("exit_code") not in (0, None) or "failed" in str(e.get("output_summary", "")).lower()) for e in recent):
        return "debugging"
    if any(e.get("event_type") == "git_branch_changed" for e in recent):
        return "working on branch"
    if any(e.get("event_type") == "file_modified" for e in recent):
        return "editing code"
    return None
