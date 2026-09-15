from typing import Any, Dict

from app.task.task_models import StructuredTask


def build_plan(task: StructuredTask) -> Dict[str, Any]:
    return {"operation": task.action or "cloud_task", "target": task.target}
