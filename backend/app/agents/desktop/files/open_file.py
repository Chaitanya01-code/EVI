from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from app.agents.desktop.files.search_file import search_file


def open_file(file_path: str) -> Dict[str, Any]:
    """Open a file with the system default application."""
    if not file_path:
        return {"success": False, "verified": False, "message": "No file specified to open."}

    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        # Search for file if not an absolute or existing path
        search_res = search_file(file_path)
        if search_res.get("ambiguous"):
            return search_res
        if search_res.get("success") and search_res.get("path"):
            path = Path(search_res["path"])
        else:
            return {"success": False, "verified": False, "message": f"File '{file_path}' does not exist."}

    try:
        if os.name == "nt":
            os.startfile(str(path))
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return {"success": True, "verified": True, "message": f"Opened {path.name}."}
    except Exception:
        return {"success": False, "verified": False, "message": f"Could not open {path.name}."}
