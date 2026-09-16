from __future__ import annotations

import os
import subprocess
from typing import Any, Dict


def restart(confirm: bool = False) -> Dict[str, Any]:
    """Restart the computer with mandatory policy confirmation."""
    if not confirm:
        return {
            "success": False,
            "verified": False,
            "requires_confirmation": True,
            "message": "Restarting the computer requires confirmation. Please confirm to proceed.",
        }

    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Restart is only supported on Windows."}

    try:
        # Give a 30 second abortable grace window
        subprocess.run(["shutdown", "/r", "/t", "30"], check=True)
        return {
            "success": True,
            "verified": True,
            "message": "Computer will restart in 30 seconds. Run 'shutdown /a' in terminal to cancel.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not initiate restart: {str(e)}"}
