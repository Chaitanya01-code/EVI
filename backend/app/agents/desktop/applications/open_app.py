from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

from app.agents.desktop.applications.find_app import find_app


def open_app(app_name: str) -> Dict[str, Any]:
    """Launch a Windows application dynamically."""
    if not app_name:
        return {"success": False, "verified": False, "message": "No application specified."}

    app = getattr(open_app, "find_app", find_app)(app_name)
    if app is None:
        # Fallback: attempt direct startfile or command execution
        try:
            if os.name == "nt":
                os.startfile(app_name)
                return {
                    "success": True,
                    "verified": False,
                    "message": f"{app_name} was opened.",
                    "target": app_name,
                    "process_name": f"{app_name}.exe",
                }
        except Exception:
            pass
        return {"success": False, "verified": False, "message": f"I couldn't find {app_name}."}

    try:
        if os.name == "nt" and app.command.lower().endswith(".lnk"):
            os.startfile(app.command)
        else:
            subprocess.Popen(
                [app.command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        return {
            "success": True,
            "verified": False,
            "message": f"{app.name} was opened.",
            "target": app.name,
            "process_name": app.process_name or f"{app.name}.exe",
        }
    except (OSError, subprocess.SubprocessError):
        return {"success": False, "verified": False, "message": f"I couldn't open {app.name}."}


open_app.find_app = find_app
