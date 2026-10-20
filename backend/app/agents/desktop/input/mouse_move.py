from __future__ import annotations

import ctypes
import os
from typing import Any, Dict

from app.phase4.computer.controller import DesktopAutomationController
from app.safety.executor_gate import run_guarded_tool_sync


_controller = DesktopAutomationController()


def mouse_move(x: int, y: int) -> Dict[str, Any]:
    """Move mouse cursor to (x, y) coordinates."""
    return run_guarded_tool_sync(
        "computer.mouse_move",
        {"x": x, "y": y},
        "desktop_agent",
        lambda: _controller.move_mouse(x, y),
    )
