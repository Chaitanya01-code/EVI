from typing import Any, Dict

from app.task.task_models import StructuredTask


def build_plan(task: StructuredTask) -> Dict[str, Any]:
    action = task.action or "browser_task"
    if action == "navigate":
        action = "open_url"
    return {"category": task.category or "navigation", "operation": action, "target": task.target}
