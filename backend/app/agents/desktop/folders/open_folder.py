from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict


def open_folder(folder_path: str) -> Dict[str, Any]:
    """Open a folder in Windows File Explorer."""
    if not folder_path:
        return {"success": False, "verified": False, "message": "No folder path provided to open."}

    path = Path(folder_path).expanduser().resolve()
    if not path.exists():
        # Check in user home
        for candidate in ("Documents", "Desktop", "Downloads", "Projects"):
            p = Path.home() / candidate / folder_path
            if p.exists() and p.is_dir():
                path = p
                break
        else:
            p = Path.home() / folder_path
            if p.exists() and p.is_dir():
                path = p
            else:
                return {"success": False, "verified": False, "message": f"Folder '{folder_path}' does not exist."}

    try:
        if os.name == "nt":
            os.startfile(str(path))
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return {"success": True, "verified": True, "message": f"Opened folder {path.name}."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not open folder: {str(e)}"}
