from __future__ import annotations

import ctypes
import os
from typing import Any, Dict

from app.phase4.computer.controller import DesktopAutomationController


_controller = DesktopAutomationController()


def mouse_move(x: int, y: int) -> Dict[str, Any]:
    """Move mouse cursor to (x, y) coordinates."""
    return _controller.move_mouse(x, y)
