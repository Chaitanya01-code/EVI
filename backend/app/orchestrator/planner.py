from __future__ import annotations

from typing import Any, Dict, List

from app.task.task_models import StructuredTask
from app.orchestrator.models import ExecutionPlan, TaskDependency, TaskStep


_AGENT_BY_TYPE = {
    "desktop": "desktop",
    "browser": "browser",
    "coding": "coding",
    "cloud": "cloud",
}


def _step_from_source(task: StructuredTask, source: Dict[str, Any], index: int) -> TaskStep:
    agent_type = str(source.get("task_type", "unknown"))
    action = str(source.get("action", ""))
    target = str(source.get("target", ""))
    dependencies = source.get("depends_on", [])
    if "depends_on" not in source and index:
        dependencies = [f"step-{index}"]
    arguments = dict(source.get("arguments", source.get("params", {})))
    arguments.setdefault("category", str(source.get("category", "")))
    return TaskStep(
        step_id=f"step-{index + 1}",
        task_id=task.task_id,
        description=str(source.get("description", action or target)),
        agent_type=_AGENT_BY_TYPE.get(agent_type, agent_type),
        action=action,
        target=target,
        arguments=arguments,
        depends_on=[TaskDependency(step_id=str(step)) for step in dependencies],
    )


def build_plan(task: StructuredTask) -> ExecutionPlan:
    """Build an execution graph from Task Understanding output, without agent calls."""
    sources: List[Dict[str, Any]] = list(task.steps)
    if not sources:
        sources = [{
            "task_type": task.task_type.value,
            "category": task.category,
            "action": task.action,
            "target": task.target,
            "description": task.original_text,
        }]
    steps = [_step_from_source(task, source, index) for index, source in enumerate(sources)]
    return ExecutionPlan(task_id=task.task_id, steps=steps)
