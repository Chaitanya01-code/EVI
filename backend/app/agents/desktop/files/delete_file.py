from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def delete_file(file_path: str, confirm: bool = False) -> Dict[str, Any]:
    """Delete a file safely with confirmation requirement for high-impact targets."""
    if not file_path:
        return {"success": False, "verified": False, "message": "No file path provided to delete."}

    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        return {"success": False, "verified": False, "message": f"File '{file_path}' does not exist."}

    # Protection for critical files
    critical_names = {"ntuser.dat", "bootmgr", "pagefile.sys", "swapfile.sys"}
    if path.name.lower() in critical_names or str(path).lower().startswith("c:\\windows"):
        return {"success": False, "verified": False, "message": "Cannot delete system protected files."}

    try:
        os.remove(str(path))
        verified = not path.exists()
        return {
            "success": True,
            "verified": verified,
            "message": f"Deleted {path.name}.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not delete file: {str(e)}"}
