from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move a file to a new destination."""
    if not source or not destination:
        return {"success": False, "verified": False, "message": "Source and destination paths are required."}

    src_path = Path(source).expanduser().resolve()
    dst_path = Path(destination).expanduser().resolve()

    if not src_path.exists() or not src_path.is_file():
        return {"success": False, "verified": False, "message": f"Source file '{source}' does not exist."}

    try:
        if dst_path.is_dir():
            target_file = dst_path / src_path.name
        else:
            target_file = dst_path
            target_file.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_path), str(target_file))
        verified = target_file.exists() and not src_path.exists()
        return {
            "success": True,
            "verified": verified,
            "message": f"Moved {src_path.name} to {target_file}.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not move file: {str(e)}"}
