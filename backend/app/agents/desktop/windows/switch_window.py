from __future__ import annotations

import os
from typing import Any, Dict

from app.agents.desktop.windows.utils import find_window_by_target, win32con, win32gui


def switch_window(target: str) -> Dict[str, Any]:
    """Switch/bring to foreground the specified application window."""
    if not target:
        return {"success": False, "verified": False, "message": "No target window specified."}

    if os.name != "nt" or win32gui is None:
        return {"success": False, "verified": False, "message": "Window manipulation is only supported on Windows with pywin32."}

    found = find_window_by_target(target)
    if not found:
        return {"success": False, "verified": False, "message": f"Could not find a window matching '{target}'."}

    hwnd, title = found
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return {"success": True, "verified": True, "message": f"Switched to {title}."}
    except Exception:
        return {"success": False, "verified": False, "message": f"Could not bring {title} to the foreground."}
