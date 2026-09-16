from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


def move_folder(source: str, destination: str) -> Dict[str, Any]:
    """Move a folder to a new destination."""
    if not source or not destination:
        return {"success": False, "verified": False, "message": "Source and destination folder paths are required."}

    src_path = Path(source).expanduser().resolve()
    dst_path = Path(destination).expanduser().resolve()

    if not src_path.exists() or not src_path.is_dir():
        return {"success": False, "verified": False, "message": f"Source folder '{source}' does not exist."}

    try:
        dst_path.mkdir(parents=True, exist_ok=True)
        target_dir = dst_path / src_path.name
        shutil.move(str(src_path), str(target_dir))
        verified = target_dir.exists() and not src_path.exists()
        return {
            "success": True,
            "verified": verified,
            "message": f"Moved folder '{src_path.name}' to {target_dir}.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not move folder: {str(e)}"}
