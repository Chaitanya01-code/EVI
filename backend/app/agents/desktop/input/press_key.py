from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict

from app.phase4.computer.controller import DesktopAutomationController


_controller = DesktopAutomationController()


def press_key(key: str) -> Dict[str, Any]:
    """Press and release a keyboard key."""
    return _controller.press_key(key)
