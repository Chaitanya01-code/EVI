from __future__ import annotations

import ctypes
import os
from typing import Any, Dict


def sleep(confirm: bool = False) -> Dict[str, Any]:
    """Put the computer to sleep with policy confirmation."""
    if not confirm:
        return {
            "success": False,
            "verified": False,
            "requires_confirmation": True,
            "message": "Putting the computer to sleep requires confirmation. Please confirm to proceed.",
        }

    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Sleep is only supported on Windows."}

    try:
        # SetSuspendState(bHibernate=False, bForce=False, bWakeupEventsDisabled=False)
        ctypes.windll.PowrProf.SetSuspendState(0, 0, 0)
        return {"success": True, "verified": True, "message": "Computer entered sleep mode."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not put computer to sleep: {str(e)}"}
