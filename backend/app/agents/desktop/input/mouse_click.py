from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict, Optional

from app.phase4.computer.controller import DesktopAutomationController
from app.safety.executor_gate import run_guarded_tool_sync


_controller = DesktopAutomationController()


def mouse_click(button: str = "left", double: bool = False, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    """Click mouse button at current or specified coordinates."""
    if x is None or y is None:
        return {"success": False, "verified": False, "message": "x and y coordinates are required."}
    if double:
        if button.lower() != "left":
            return {"success": False, "verified": False, "message": "Double-click only supports the left button."}
        tool = "computer.double_click"
        run = lambda: _controller.double_click(x, y)
    else:
        tool = "computer.click"
        run = lambda: _controller.click(x, y, button)
    return run_guarded_tool_sync(
        tool,
        {"button": button, "double": double, "x": x, "y": y},
        "desktop_agent",
        run,
    )
