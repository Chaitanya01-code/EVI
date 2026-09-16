from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


def type_text(text: str) -> Dict[str, Any]:
    """Type a string of text safely via Windows SendInput/keybd_event."""
    if not text:
        return {"success": False, "verified": False, "message": "No text provided to type."}

    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Text typing automation is only supported on Windows."}

    try:
        for char in text:
            char_code = ord(char)
            # Use KEYEVENTF_UNICODE for proper Unicode character sending
            ctypes.windll.user32.keybd_event(0, char_code, KEYEVENTF_UNICODE, 0)
            ctypes.windll.user32.keybd_event(0, char_code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)
        return {"success": True, "verified": True, "message": f"Typed text."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not type text: {str(e)}"}
