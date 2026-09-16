from __future__ import annotations

from typing import Any, Dict


def find_ui_element(element_name: str) -> Dict[str, Any]:
    """Basic interface to find a UI element on screen for future visual automation."""
    if not element_name:
        return {"success": False, "verified": False, "message": "No UI element specified to find."}

    return {
        "success": False,
        "verified": False,
        "element": element_name,
        "message": f"Visual element detection for '{element_name}' is not yet enabled. Basic interface ready.",
    }
