from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict

from app.phase4.computer.controller import DesktopAutomationController
from app.safety.executor_gate import run_guarded_tool_sync


_controller = DesktopAutomationController()


def press_key(key: str) -> Dict[str, Any]:
    """Press and release a keyboard key."""
    return run_guarded_tool_sync(
        "computer.press_key",
        {"key": key},
        "desktop_agent",
        lambda: _controller.press_key(key),
    )
