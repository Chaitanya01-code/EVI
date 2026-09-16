from __future__ import annotations

import os
from typing import Any, Dict

from app.agents.desktop.windows.utils import find_window_by_target, win32gui


def resize_window(target: str, width: int = 1024, height: int = 768) -> Dict[str, Any]:
    """Resize the specified application window to the given dimensions."""
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
        x, y = rect[0], rect[1]
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
        return {"success": True, "verified": True, "message": f"Resized {title} to {width}x{height}."}
    except Exception:
        return {"success": False, "verified": False, "message": f"Could not resize {title}."}
