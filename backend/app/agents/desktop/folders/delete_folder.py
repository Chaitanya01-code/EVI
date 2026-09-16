from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


def delete_folder(folder_path: str, confirm: bool = False) -> Dict[str, Any]:
    """Delete a folder safely with confirmation and system directory protection."""
    if not folder_path:
        return {"success": False, "verified": False, "message": "No folder path provided."}

    path = Path(folder_path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        return {"success": False, "verified": False, "message": f"Folder '{folder_path}' does not exist."}

    # Protected root and system directories
    norm = str(path).lower()
    if norm in ("c:\\", "c:\\windows", "c:\\program files", "c:\\program files (x86)", str(Path.home()).lower()):
        return {"success": False, "verified": False, "message": "Cannot delete critical system or root folder."}

    try:
        shutil.rmtree(str(path))
        verified = not path.exists()
        return {
            "success": True,
            "verified": verified,
            "message": f"Deleted folder '{path.name}'.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not delete folder: {str(e)}"}
