from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from app.agents.desktop.applications.find_app import find_app
from app.agents.desktop.windows.utils import find_window_by_target


def verify_plan(plan: Dict[str, Any], execution: Dict[str, Any]) -> bool:
    """Verify execution outcome of desktop actions."""
    if not execution.get("success"):
        return False

    action = plan.get("action") or plan.get("operation") or ""
    category = plan.get("category", "")
    target = str(plan.get("target", ""))
    params = plan.get("params", {})

    # If already verified by the tool directly
    if execution.get("verified") and action not in ("open_app", "open_application", "close_app", "close_application"):
        return True

    # Verification for Applications
    if action in ("open_app", "open_application", "close_app", "close_application", "restart_app", "restart_application"):
        if os.name != "nt":
            return bool(execution.get("verified", False))

        try:
            check = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            app = find_app(target)
            process_candidates = []
            if app and app.process_name:
                process_candidates.append(app.process_name.lower())
            if execution.get("process_name"):
                process_candidates.append(str(execution["process_name"]).lower())
            if target:
                process_candidates.extend([f"{target.lower()}.exe", target.lower()])
                known_aliases = {
                    "visual studio code": "code.exe",
                    "vs code": "code.exe",
                    "chrome": "chrome.exe",
                    "google chrome": "chrome.exe",
                    "notepad": "notepad.exe",
                    "calculator": "calculatorapp.exe",
                    "calc": "calculatorapp.exe",
                }
                if target.lower() in known_aliases:
                    process_candidates.append(known_aliases[target.lower()])

            running = False
            tasklist_lower = check.stdout.lower()
            for proc in process_candidates:
                if proc in tasklist_lower:
                    running = True
                    break

            # Also check visible window titles
            if not running and find_window_by_target(target):
                running = True

            if action in ("close_app", "close_application"):
                return not running
            return running
        except (OSError, subprocess.SubprocessError):
            return bool(execution.get("success"))

    # Verification for Folders
    if action == "create_folder":
        folder_path = execution.get("path") or params.get("folder_name")
        if folder_path and os.path.isdir(folder_path):
            return True
        return Path(Path.home() / "Documents" / target).exists()

    # Verification for Files
    if action in ("rename_file", "copy_file", "move_file"):
        dst = params.get("destination")
        if dst and os.path.exists(dst):
            return True

    return bool(execution.get("verified", execution.get("success", False)))
