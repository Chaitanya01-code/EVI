import inspect
from typing import Any, Dict

from app.agents.cloud.registry import cloud_tools
from app.safety.executor_gate import run_guarded_tool_sync


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    action = plan.get("operation", "")
    tool = cloud_tools.resolve(action)
    if tool is None:
        return {"success": False, "verified": False, "message": f"Cloud action '{action}' is not supported yet."}
    try:
        names = list(inspect.signature(tool).parameters)
        arguments = {"provider": plan.get("provider", "mock"), "target": plan.get("target", "")}
        return run_guarded_tool_sync(
            action,
            arguments,
            "cloud_agent",
            lambda: tool() if not names else tool(arguments["provider"], arguments["target"]),
        )
    except (OSError, TypeError, ValueError) as error:
        return {"success": False, "verified": False, "message": f"I couldn't complete that cloud action: {error}"}
