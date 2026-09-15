from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    if plan.get("operation") != "open_application" or plan.get("target") != "Visual Studio Code":
        return {"success": False, "message": "I can only open Visual Studio Code right now."}

    command = shutil.which("code") or shutil.which("code.cmd")
    if not command and os.name == "nt":
        command = "code.cmd"
    if not command:
        return {"success": False, "message": "I couldn't find Visual Studio Code on this computer."}

    try:
        subprocess.Popen([command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "message": "Visual Studio Code was opened."}
    except OSError:
        return {"success": False, "message": "I couldn't open Visual Studio Code."}
