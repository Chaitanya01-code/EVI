from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def rename_folder(source: str, destination: str) -> Dict[str, Any]:
    """Rename a folder."""
    if not source or not destination:
        return {"success": False, "verified": False, "message": "Source and destination folder names are required."}

    src_path = Path(source).expanduser().resolve()
    if not src_path.exists() or not src_path.is_dir():
        # Check in Documents
        p = Path.home() / "Documents" / source
        if p.exists() and p.is_dir():
            src_path = p
        else:
            return {"success": False, "verified": False, "message": f"Folder '{source}' does not exist."}

    dst_name = Path(destination).name
    dst_path = src_path.parent / dst_name

    try:
        src_path.rename(dst_path)
        verified = dst_path.exists() and dst_path.is_dir() and not src_path.exists()
        return {
            "success": True,
            "verified": verified,
            "message": f"Renamed folder '{src_path.name}' to '{dst_path.name}'.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not rename folder: {str(e)}"}
