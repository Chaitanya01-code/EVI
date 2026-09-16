from __future__ import annotations

import os
import subprocess
from typing import Any, Dict


def shutdown(confirm: bool = False) -> Dict[str, Any]:
    """Shut down the computer with mandatory policy confirmation."""
    if not confirm:
        return {
            "success": False,
            "verified": False,
            "requires_confirmation": True,
            "message": "Shutting down the computer requires confirmation. Please confirm to proceed.",
        }

    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Shutdown is only supported on Windows."}

    try:
        # Give a 30 second abortable grace window
        subprocess.run(["shutdown", "/s", "/t", "30"], check=True)
        return {
            "success": True,
            "verified": True,
            "message": "Computer will shut down in 30 seconds. Run 'shutdown /a' in terminal to cancel.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not initiate shutdown: {str(e)}"}
