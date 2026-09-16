import inspect
from typing import Any, Dict

from app.agents.browser.registry import browser_tools


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    action = plan.get("operation", "")
    tool = browser_tools.resolve(action)
    if tool is None:
        return {"success": False, "verified": False, "message": f"Browser action '{action}' is not supported yet."}
    try:
        parameters = [name for name in inspect.signature(tool).parameters]
        if not parameters:
            return tool()
        return tool(plan.get("target", ""))
    except (OSError, TypeError, ValueError) as error:
        return {"success": False, "verified": False, "message": f"I couldn't complete that browser action: {error}"}
