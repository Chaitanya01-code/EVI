from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict

from app.phase4.computer.controller import DesktopAutomationController
from app.safety.executor_gate import run_guarded_tool_sync


_controller = DesktopAutomationController()


def type_text(text: str) -> Dict[str, Any]:
    """Type a string of text safely via Windows SendInput/keybd_event."""
    return run_guarded_tool_sync(
        "computer.type_text",
        {"text": text},
        "desktop_agent",
        lambda: _controller.type_text(text),
    )
