from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict

# Virtual Key Codes
VK_MAP = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "escape": 0x1B,
    "esc": 0x1B,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "win": 0x5B,
    "windows": 0x5B,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}
KEYEVENTF_KEYUP = 0x0002


def press_key(key: str) -> Dict[str, Any]:
    """Press and release a keyboard key."""
    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Key automation is only supported on Windows."}

    norm_key = key.lower().strip()
    vk_code = VK_MAP.get(norm_key)

    if vk_code is None:
        if len(norm_key) == 1:
            vk_code = ctypes.windll.user32.VkKeyScanW(ord(norm_key)) & 0xFF
        else:
            return {"success": False, "verified": False, "message": f"Unsupported key: '{key}'."}

    try:
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        return {"success": True, "verified": True, "message": f"Pressed {key}."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not press key '{key}': {str(e)}"}
