from __future__ import annotations

import ctypes
import os
from typing import Any, Dict


def lock() -> Dict[str, Any]:
    """Lock the Windows workstation safely."""
    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Workstation lock is only supported on Windows."}

    try:
        res = ctypes.windll.user32.LockWorkStation()
        if res:
            return {"success": True, "verified": True, "message": "Workstation has been locked."}
        return {"success": False, "verified": False, "message": "Failed to lock workstation."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not lock workstation: {str(e)}"}
