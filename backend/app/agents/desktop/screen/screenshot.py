from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict


def screenshot(output_path: str = "") -> Dict[str, Any]:
    """Capture a screenshot of the primary display without sending it externally."""
    if os.name != "nt":
        return {"success": False, "verified": False, "message": "Screenshot capture is only supported on Windows."}

    if not output_path:
        temp_dir = Path(tempfile.gettempdir()) / "evi_screenshots"
        temp_dir.mkdir(parents=True, exist_ok=True)
        target_file = temp_dir / "latest_screenshot.png"
    else:
        target_file = Path(output_path).expanduser().resolve()
        target_file.parent.mkdir(parents=True, exist_ok=True)

    # Windows native PowerShell script to capture screen without extra dependencies
    ps_cmd = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height; "
        "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
        "$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size); "
        f"$bitmap.Save('{str(target_file)}', [System.Drawing.Imaging.ImageFormat]::Png); "
        "$graphics.Dispose(); "
        "$bitmap.Dispose();"
    )

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if res.returncode == 0 and target_file.exists():
            return {
                "success": True,
                "verified": True,
                "path": str(target_file),
                "message": f"Screenshot saved to {target_file}.",
            }
        return {"success": False, "verified": False, "message": "Failed to capture screenshot."}
    except Exception as e:
        return {"success": False, "verified": False, "message": f"Could not take screenshot: {str(e)}"}
