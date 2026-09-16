from __future__ import annotations

import ctypes
import os
from typing import Any, Dict


def mouse_move(x: int, y: int) -> Dict[str, Any]:
    """Move mouse cursor to (x, y) coordinates."""
    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Mouse automation is only supported on Windows."}

    try:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        return {"success": True, "verified": True, "message": f"Mouse moved to ({x}, {y})."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not move mouse: {str(e)}"}
