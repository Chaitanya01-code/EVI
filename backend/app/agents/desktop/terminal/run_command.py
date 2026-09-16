from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, Tuple

_LAST_OUTPUT: Dict[str, str] = {"stdout": "", "stderr": "", "command": ""}


def classify_command(cmd: str) -> Tuple[str, str]:
    """Classify a terminal command as 'safe', 'requires_confirmation', or 'blocked'."""
    c = cmd.strip().lower()

    # Blocked: Extreme destructive actions
    blocked_patterns = (
        r"\bformat\b",
        r"\brmdir\b.*[c-z]:",
        r"\bdel\b.*[c-z]:\\windows",
        r"\breg\s+delete\s+hklm",
        r":\(\)\s*\{.*\};\s*:",  # fork bomb
    )
    for p in blocked_patterns:
        if re.search(p, c):
            return "blocked", "This command poses severe risk to system integrity and is blocked."

    # Requires confirmation: State modifications or software installations
    confirm_patterns = (
        r"\b(npm|pip|pip3|yarn|pnpm)\s+(install|uninstall|update)\b",
        r"\bgit\s+(reset\s+--hard|clean\s+-fd|push\s+--force)\b",
        r"\bnetsh\b",
        r"\bdiskpart\b",
        r"\bvssadmin\b",
        r"\bpowershell\s+.*-executionpolicy\s+bypass\b",
    )
    for p in confirm_patterns:
        if re.search(p, c):
            return "requires_confirmation", "This command alters package or system state and requires confirmation."

    return "safe", "Command is safe to execute."


def run_command(command: str, cwd: str = "", confirm: bool = False) -> Dict[str, Any]:
    """Execute a protected terminal command."""
    if not command:
        return {"success": False, "verified": False, "message": "No command provided."}

    level, reason = classify_command(command)
    if level == "blocked":
        return {"success": False, "verified": False, "blocked": True, "message": reason}

    if level == "requires_confirmation" and not confirm:
        return {
            "success": False,
            "verified": False,
            "requires_confirmation": True,
            "message": f"Confirmation required: {reason} Use confirm=True to proceed.",
        }

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        _LAST_OUTPUT["stdout"] = proc.stdout
        _LAST_OUTPUT["stderr"] = proc.stderr
        _LAST_OUTPUT["command"] = command

        output_text = (proc.stdout or proc.stderr or "(Command executed with no output)").strip()
        return {
            "success": proc.returncode == 0,
            "verified": proc.returncode == 0,
            "returncode": proc.returncode,
            "output": output_text,
            "message": f"Command finished with code {proc.returncode}.",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "verified": False, "message": "Command timed out after 15 seconds."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Failed to execute command: {str(e)}"}
