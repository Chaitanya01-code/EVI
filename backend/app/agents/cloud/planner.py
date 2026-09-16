from typing import Any, Dict

from app.task.task_models import StructuredTask


def build_plan(task: StructuredTask) -> Dict[str, Any]:
    target = task.target or ""
    provider = "mock"
    lowered = target.lower()
    for candidate in ("aws", "azure", "gcp", "mock"):
        if candidate in lowered:
            provider = candidate
            break
    return {
        "category": task.category or "cloud",
        "operation": task.action or "cloud_task",
        "target": target,
        "provider": provider,
    }
