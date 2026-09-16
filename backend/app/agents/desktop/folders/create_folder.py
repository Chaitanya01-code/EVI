from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def create_folder(folder_name: str, location: str = "") -> Dict[str, Any]:
    """Create a new folder at location or within user Documents/home."""
    if not folder_name:
        return {"success": False, "verified": False, "message": "No folder name provided."}

    if location:
        base_loc = Path(location).expanduser()
        if not base_loc.is_absolute():
            # Check user directories
            for candidate in ("Documents", "Desktop", "Downloads", "Projects"):
                p = Path.home() / candidate / location
                if p.exists():
                    base_loc = p
                    break
            else:
                p = Path.home() / location
                base_loc = p if p.exists() else (Path.home() / "Documents" / location)
    else:
        base_loc = Path.home() / "Documents"

    target_dir = base_loc / folder_name
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        verified = target_dir.exists() and target_dir.is_dir()
        return {
            "success": True,
            "verified": verified,
            "path": str(target_dir),
            "message": f"Created folder '{folder_name}' at {target_dir}.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not create folder: {str(e)}"}
