from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict

from app.phase4.computer.controller import DesktopAutomationController


_controller = DesktopAutomationController()


def type_text(text: str) -> Dict[str, Any]:
    """Type a string of text safely via Windows SendInput/keybd_event."""
    return _controller.type_text(text)
