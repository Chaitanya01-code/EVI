from __future__ import annotations

import inspect
import logging
from typing import Any, Dict

from app.agents.desktop.registry import desktop_tools

logger = logging.getLogger(__name__)


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a planned desktop action via the DesktopToolRegistry."""
    action = plan.get("action") or plan.get("operation") or ""
    category = plan.get("category", "")
    target = plan.get("target", "")
    params = dict(plan.get("params", {}))

    # Look up tool in registry
    tool = desktop_tools.resolve(f"{category}.{action}" if category and "." not in action else action)
    if tool is None:
        tool = desktop_tools.resolve(action)

    if tool is None:
        return {
            "success": False,
            "verified": False,
            "message": f"Desktop action '{action}' is not supported.",
        }

    try:
        sig = inspect.signature(tool)
        param_names = list(sig.parameters.keys())

        # If tool takes no parameters
        if not param_names:
            return tool()

        # Build kwargs matching tool signature
        call_kwargs = {}
        for p_name in param_names:
            if p_name in params:
                call_kwargs[p_name] = params[p_name]
            elif p_name in ("app_name", "target", "element_name", "key", "text", "file_path", "folder_path", "command") and target:
                call_kwargs[p_name] = target

        # If no kwargs matched, pass target as first argument if available
        if not call_kwargs and target and len(param_names) >= 1:
            call_kwargs[param_names[0]] = target

        result = tool(**call_kwargs)
        if isinstance(result, dict):
            return result
        return {"success": True, "verified": True, "message": str(result)}

    except Exception as e:
        logger.exception("Desktop tool execution failed")
        return {
            "success": False,
            "verified": False,
            "message": f"Failed to execute desktop operation: {str(e)}",
        }
