from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.core.classify import _generate_llm
from app.task.task_models import StructuredTask

logger = logging.getLogger(__name__)


class DesktopPlan(BaseModel):
    category: str = Field(description="Category: applications, windows, files, folders, system, input, screen, terminal")
    action: str = Field(description="Action name e.g. open_app, close_app, switch_window, create_folder, rename_file, run_command, shutdown")
    target: str = Field(default="", description="Target entity, e.g. application name, file name, window title")
    folder_name: str = Field(default="")
    location: str = Field(default="")
    source: str = Field(default="")
    destination: str = Field(default="")
    command: str = Field(default="")
    confirm: bool = Field(default=False)


_PLANNER_PROMPT = """
You are EVI's Desktop Task Planner. Translate the user's natural language request into a single structured desktop action.

Available categories and actions:
- applications: open_app, close_app, restart_app, list_apps, find_app
- windows: switch_window, minimize_window, maximize_window, resize_window, move_window
- files: open_file, copy_file, move_file, rename_file, delete_file, search_file
- folders: create_folder, open_folder, rename_folder, move_folder, delete_folder
- system: shutdown, restart, lock, sleep
- input: mouse_click, mouse_move, type_text, press_key
- screen: screenshot, inspect_screen, find_ui_element
- terminal: run_command, run_script, get_output

Parameters convention:
- For folders.create_folder: {"folder_name": "...", "location": "..."}
- For files.rename_file: {"source": "...", "destination": "..."}
- For files.copy_file or move_file: {"source": "...", "destination": "..."}
- For files.open_file or delete_file: {"file_path": "..."}
- For windows.resize_window: {"width": 1024, "height": 768}
- For input.mouse_move: {"x": 100, "y": 100}
- For input.type_text: {"text": "..."}
- For input.press_key: {"key": "..."}
- For terminal.run_command: {"command": "..."}

Return JSON with exactly: category, action, target, params.
""".strip()


def _fallback_plan(task: StructuredTask) -> Dict[str, Any]:
    category = task.category or "applications"
    action = task.action or "open_app"
    target = task.target or ""
    params: Dict[str, Any] = {}
    text = task.original_text.strip()

    # Normalization of action name
    if action in ("open_application", "open_app"):
        category = "applications"
        action = "open_app"
        params["app_name"] = target
    elif action in ("close_application", "close_app"):
        category = "applications"
        action = "close_app"
        params["app_name"] = target
    elif action in ("restart_application", "restart_app"):
        category = "applications"
        action = "restart_app"
        params["app_name"] = target

    # Folders
    create_folder_match = re.search(r"\bcreate\s+(?:a\s+)?folder\s+(?:called\s+|named\s+)?([^\s]+)(?:\s+(?:in|inside)\s+(.+))?", text, re.I)
    if create_folder_match:
        category = "folders"
        action = "create_folder"
        name = create_folder_match.group(1).strip("'\"")
        loc = (create_folder_match.group(2) or "").strip("'\"")
        target = name
        params = {"folder_name": name, "location": loc}

    # Rename file
    rename_file_match = re.search(r"\brename\s+(?:file\s+)?([^\s]+)\s+(?:to\s+)([^\s]+)", text, re.I)
    if rename_file_match:
        category = "files"
        action = "rename_file"
        src = rename_file_match.group(1).strip("'\"")
        dst = rename_file_match.group(2).strip("'\"")
        target = src
        params = {"source": src, "destination": dst}

    # Copy file
    copy_file_match = re.search(r"\bcopy\s+(?:file\s+)?([^\s]+)\s+(?:to\s+)([^\s]+)", text, re.I)
    if copy_file_match:
        category = "files"
        action = "copy_file"
        src = copy_file_match.group(1).strip("'\"")
        dst = copy_file_match.group(2).strip("'\"")
        target = src
        params = {"source": src, "destination": dst}

    # Move file
    move_file_match = re.search(r"\bmove\s+(?:file\s+)?([^\s]+)\s+(?:to\s+)([^\s]+)", text, re.I)
    if move_file_match:
        category = "files"
        action = "move_file"
        src = move_file_match.group(1).strip("'\"")
        dst = move_file_match.group(2).strip("'\"")
        target = src
        params = {"source": src, "destination": dst}

    # Windows
    if "switch to" in text.lower():
        category = "windows"
        action = "switch_window"
        params["target"] = target
    elif "minimize" in text.lower():
        category = "windows"
        action = "minimize_window"
        params["target"] = target
    elif "maximize" in text.lower():
        category = "windows"
        action = "maximize_window"
        params["target"] = target

    # System
    if text.lower().startswith("shutdown") or "shut down" in text.lower():
        category = "system"
        action = "shutdown"
    elif text.lower().startswith("restart pc") or text.lower().startswith("reboot"):
        category = "system"
        action = "restart"
    elif "lock" in text.lower() and "computer" in text.lower() or text.lower() == "lock":
        category = "system"
        action = "lock"

    # Terminal
    if text.lower().startswith("run command") or text.lower().startswith("terminal"):
        category = "terminal"
        action = "run_command"
        cmd = re.sub(r"^(?:run\s+command|terminal|run)\s*", "", text, flags=re.I).strip()
        params = {"command": cmd}

    return {
        "category": category,
        "action": action,
        "target": target,
        "params": params,
        "operation": action,  # Backwards compatibility
    }


def build_plan(task: StructuredTask) -> Dict[str, Any]:
    """Convert natural language task into structured desktop action."""
    try:
        response = _generate_llm(
            f"{_PLANNER_PROMPT}\n\nTask: {task.original_text}\nStructured: {task.model_dump_json()}",
            response_schema=DesktopPlan,
        )
        plan = DesktopPlan.model_validate_json(response.text)
        plan_dict = plan.model_dump()
        plan_dict["operation"] = plan_dict["action"]
        plan_dict["params"] = {
            k: v for k, v in {
                "folder_name": plan.folder_name,
                "location": plan.location,
                "source": plan.source,
                "destination": plan.destination,
                "command": plan.command,
                "confirm": plan.confirm,
            }.items() if v
        }
        return plan_dict
    except Exception:
        logger.exception("LLM desktop plan generation failed; using fallback")

    return _fallback_plan(task)
