from __future__ import annotations

import inspect
import logging
from typing import Any, Dict

from app.agents.desktop.registry import desktop_tools
from app.safety.executor_gate import run_guarded_tool_sync

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
        call_kwargs = {}
        if param_names:
            parameter_aliases = {
                "file_path": "path",
                "folder_path": "path",
            }
            for p_name in param_names:
                if p_name in params:
                    call_kwargs[p_name] = params[p_name]
                elif parameter_aliases.get(p_name) in params:
                    call_kwargs[p_name] = params[parameter_aliases[p_name]]
                elif p_name in ("app_name", "target", "element_name", "key", "text", "file_path", "folder_path", "command") and target:
                    call_kwargs[p_name] = target

            if not call_kwargs and target:
                call_kwargs[param_names[0]] = target

        resolved_name = f"{category}.{action}" if category and "." not in action else action
        guarded_by_tool = resolved_name in {
            "input.mouse_click",
            "input.mouse_move",
            "input.press_key",
            "input.type_text",
            "applications.open_app",
            "applications.close_app",
            "applications.find_app",
            "applications.list_installed_apps",
            "applications.list_apps",
            "applications.force_close_app",
            "applications.list_running_apps",
            "applications.focus_app",
            "windows.switch_window",
            "files.open_file", "files.copy_file", "files.move_file", "files.rename_file",
            "files.delete_file", "files.search_file", "files.list_dir", "files.search_files",
            "files.search_in_files", "files.file_info", "files.read_file", "files.create_file",
            "files.write_file", "files.create_docx", "files.create_xlsx",
            "files.open_in_explorer", "files.bulk_file_operation",
            "files.copy", "files.move", "files.delete",
            "folders.create_folder", "folders.open_folder", "folders.rename_folder",
            "folders.move_folder", "folders.delete_folder",
        } or action in {
            "mouse_click", "mouse_move", "press_key", "type_text",
            "open_app", "close_app", "find_app", "list_installed_apps",
            "list_apps", "force_close_app", "list_running_apps", "focus_app",
            "switch_window",
            "open_file", "copy_file", "move_file", "rename_file", "delete_file",
            "search_file", "list_dir", "search_files", "search_in_files", "file_info",
            "read_file", "create_file", "write_file", "create_docx", "create_xlsx",
            "open_in_explorer", "bulk_file_operation", "create_folder", "open_folder",
            "rename_folder", "move_folder", "delete_folder",
            "copy", "move", "delete",
        }
        if guarded_by_tool:
            result = tool(**call_kwargs)
            return result if isinstance(result, dict) else {
                "success": True,
                "verified": True,
                "message": str(result),
            }
        return run_guarded_tool_sync(
            resolved_name,
            call_kwargs,
            "task_manager",
            lambda: tool(**call_kwargs),
        )

    except Exception as e:
        logger.exception("Desktop tool execution failed")
        return {
            "success": False,
            "verified": False,
            "message": f"Failed to execute desktop operation: {str(e)}",
        }
