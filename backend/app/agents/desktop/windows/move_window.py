from __future__ import annotations

import os
from typing import Any, Dict

from app.agents.desktop.windows.utils import find_window_by_target, win32gui


def move_window(target: str, x: int = 100, y: int = 100) -> Dict[str, Any]:
    """Move the specified application window to (x, y) coordinates."""
    if not target:
        return {"success": False, "verified": False, "message": "No target window specified."}

    if os.name != "nt" or win32gui is None:
        return {"success": False, "verified": False, "message": "Window manipulation is only supported on Windows with pywin32."}

    found = find_window_by_target(target)
    if not found:
        return {"success": False, "verified": False, "message": f"Could not find a window matching '{target}'."}

    hwnd, title = found
    try:
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
        return {"success": True, "verified": True, "message": f"Moved {title} to position ({x}, {y})."}
    except Exception:
        return {"success": False, "verified": False, "message": f"Could not move {title}."}
