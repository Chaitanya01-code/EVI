from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict, Optional

from app.phase4.computer.controller import DesktopAutomationController


_controller = DesktopAutomationController()


def mouse_click(button: str = "left", double: bool = False, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    """Click mouse button at current or specified coordinates."""
    if x is None or y is None:
        return {"success": False, "verified": False, "message": "x and y coordinates are required."}
    if double:
        return _controller.double_click(x, y) if button.lower() == "left" else {"success": False, "verified": False, "message": "Double-click only supports the left button."}
    return _controller.click(x, y, button)
