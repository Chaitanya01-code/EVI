import inspect
from typing import Any, Dict

from app.agents.coding.registry import coding_tools
from app.safety.executor_gate import run_guarded_tool_sync


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    action = plan.get("operation", "")
    tool = coding_tools.resolve(action)
    if tool is None:
        return {"success": False, "verified": False, "message": f"Coding action '{action}' is not supported yet."}
    try:
        names = list(inspect.signature(tool).parameters)
        target = plan.get("target", "")
        arguments = {} if not names else {"target": target or "evi-project" if action == "create_project" else target}
        return run_guarded_tool_sync(
            action,
            arguments,
            "coding_agent",
            lambda: tool() if not names else tool(target or "evi-project" if action == "create_project" else target),
        )
    except (OSError, TypeError, ValueError) as error:
        return {"success": False, "verified": False, "message": f"I couldn't complete that coding action: {error}"}
