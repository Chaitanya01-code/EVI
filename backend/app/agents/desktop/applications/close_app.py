from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

from app.agents.desktop.applications.find_app import find_app


def close_app(app_name: str) -> Dict[str, Any]:
    """Gracefully terminate a running Windows application."""
    if not app_name:
        return {"success": False, "verified": False, "message": "No application specified."}

    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Closing desktop applications is only supported on Windows."}

    app = find_app(app_name)
    candidates = []
    if app and app.process_name:
        candidates.append(app.process_name)
    if app:
        candidates.append(f"{app.name}.exe")
    candidates.extend([f"{app_name}.exe", app_name])

    # Remove duplicates while preserving order
    seen = set()
    process_names = [p for p in candidates if not (p.lower() in seen or seen.add(p.lower()))]

    closed_any = False
    for proc in process_names:
        try:
            res = subprocess.run(
                ["taskkill", "/IM", proc, "/T"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0:
                closed_any = True
                break
        except (OSError, subprocess.SubprocessError):
            continue

    if closed_any:
        display = app.name if app else app_name
        return {"success": True, "verified": False, "message": f"{display} was closed."}

    return {"success": False, "verified": False, "message": f"I couldn't close {app_name}."}
