import inspect
from typing import Any, Dict

from app.agents.cloud.registry import cloud_tools


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    action = plan.get("operation", "")
    tool = cloud_tools.resolve(action)
    if tool is None:
        return {"success": False, "verified": False, "message": f"Cloud action '{action}' is not supported yet."}
    try:
        names = list(inspect.signature(tool).parameters)
        if not names:
            return tool()
        return tool(plan.get("provider", "mock"), plan.get("target", ""))
    except (OSError, TypeError, ValueError) as error:
        return {"success": False, "verified": False, "message": f"I couldn't complete that cloud action: {error}"}
