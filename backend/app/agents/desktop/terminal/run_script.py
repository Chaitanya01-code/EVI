from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from app.agents.desktop.terminal.run_command import run_command


def run_script(script_path: str, args: str = "", confirm: bool = False) -> Dict[str, Any]:
    """Execute a local script (.py, .ps1, .bat) safely with policy protection."""
    if not script_path:
        return {"success": False, "verified": False, "message": "No script path provided."}

    path = Path(script_path).expanduser().resolve()
    if not path.exists():
        return {"success": False, "verified": False, "message": f"Script '{script_path}' not found."}

    ext = path.suffix.lower()
    if ext == ".py":
        cmd = f'"{sys.executable}" "{str(path)}" {args}'.strip()
    elif ext == ".ps1":
        cmd = f'powershell -ExecutionPolicy Restricted -File "{str(path)}" {args}'.strip()
    elif ext in (".bat", ".cmd"):
        cmd = f'cmd /c "{str(path)}" {args}'.strip()
    else:
        return {"success": False, "verified": False, "message": f"Unsupported script extension: {ext}"}

    return run_command(cmd, cwd=str(path.parent), confirm=confirm)
