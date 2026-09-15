from __future__ import annotations

import subprocess
from typing import Any, Dict


def verify_plan(plan: Dict[str, Any], execution: Dict[str, Any]) -> bool:
    if not execution.get("success"):
        return False
    if plan.get("target") != "Visual Studio Code":
        return False
    if not hasattr(subprocess, "run"):
        return False
    try:
        check = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Code.exe"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return "Code.exe" in check.stdout
    except (OSError, subprocess.SubprocessError):
        return False
