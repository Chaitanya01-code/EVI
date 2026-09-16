import inspect
from typing import Any, Dict

from app.agents.coding.registry import coding_tools


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    action = plan.get("operation", "")
    tool = coding_tools.resolve(action)
    if tool is None:
        return {"success": False, "verified": False, "message": f"Coding action '{action}' is not supported yet."}
    try:
        names = list(inspect.signature(tool).parameters)
        target = plan.get("target", "")
        if not names:
            return tool()
        if action == "create_project":
            return tool(target or "evi-project")
        if action in {"read_file", "search_code", "inspect_project", "detect_stack", "run_tests", "git_status", "git_diff"}:
            return tool(target)
        return tool(target)
    except (OSError, TypeError, ValueError) as error:
        return {"success": False, "verified": False, "message": f"I couldn't complete that coding action: {error}"}
