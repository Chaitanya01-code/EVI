from __future__ import annotations

from typing import Any, Dict

from app.agents.desktop.terminal.run_command import _LAST_OUTPUT


def get_output() -> Dict[str, Any]:
    """Retrieve the output of the most recently executed terminal command."""
    return {
        "success": True,
        "verified": True,
        "command": _LAST_OUTPUT.get("command", ""),
        "stdout": _LAST_OUTPUT.get("stdout", ""),
        "stderr": _LAST_OUTPUT.get("stderr", ""),
        "message": "Retrieved last command output.",
    }
