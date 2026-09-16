from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def rename_file(source: str, destination: str) -> Dict[str, Any]:
    """Rename a file."""
    if not source or not destination:
        return {"success": False, "verified": False, "message": "Source and destination file names are required."}

    src_path = Path(source).expanduser().resolve()
    if not src_path.exists() or not src_path.is_file():
        return {"success": False, "verified": False, "message": f"Source file '{source}' does not exist."}

    # If destination is just a filename, place it in the same directory as source
    dst_name = Path(destination).name
    dst_path = src_path.parent / dst_name

    try:
        src_path.rename(dst_path)
        verified = dst_path.exists() and not src_path.exists()
        return {
            "success": True,
            "verified": verified,
            "message": f"Renamed {src_path.name} to {dst_path.name}.",
        }
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not rename file: {str(e)}"}
