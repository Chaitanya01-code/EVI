from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict, Optional

# Mouse event flags
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


def mouse_click(button: str = "left", double: bool = False, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    """Click mouse button at current or specified coordinates."""
    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Mouse automation is only supported on Windows."}

    try:
        if x is not None and y is not None:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))

        btn = button.lower()
        if btn == "right":
            down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif btn == "middle":
            down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        else:
            down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

        clicks = 2 if double else 1
        for i in range(clicks):
            ctypes.windll.user32.mouse_event(down_flag, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(up_flag, 0, 0, 0, 0)
            if double and i == 0:
                time.sleep(0.05)

        action_desc = "Double-clicked" if double else "Clicked"
        return {"success": True, "verified": True, "message": f"{action_desc} {btn} mouse button."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not perform mouse click: {str(e)}"}
