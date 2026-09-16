from __future__ import annotations

import time
from typing import Any, Dict

from app.agents.desktop.applications.close_app import close_app
from app.agents.desktop.applications.open_app import open_app


def restart_app(app_name: str) -> Dict[str, Any]:
    """Restart a running desktop application."""
    close_result = close_app(app_name)
    if not close_result.get("success"):
        return {"success": False, "verified": False, "message": f"Could not close {app_name} for restart."}

    time.sleep(1.0)
    open_result = open_app(app_name)
    if not open_result.get("success"):
        return {"success": False, "verified": False, "message": f"Closed {app_name}, but could not restart it."}

    return {"success": True, "verified": False, "message": f"{app_name} was restarted."}
