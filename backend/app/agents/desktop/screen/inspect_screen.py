from __future__ import annotations

import ctypes
import os
from typing import Any, Dict


def inspect_screen() -> Dict[str, Any]:
    """Inspect screen metrics such as width, height, and display count."""
    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Screen inspection is only supported on Windows."}

    try:
        user32 = ctypes.windll.user32
        width = user32.GetSystemMetrics(0)   # SM_CXSCREEN
        height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        monitors = user32.GetSystemMetrics(80) # SM_CMONITORS or at least 1
        return {
            "success": True,
            "verified": True,
            "width": width,
            "height": height,
            "monitors": max(1, monitors),
            "message": f"Screen resolution is {width}x{height} with {max(1, monitors)} display(s).",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not inspect screen: {str(e)}"}
