from __future__ import annotations

from typing import Any, Dict

from app.agents.desktop.applications.installed_apps import open_app as guarded_open_app


def open_app(app_name: str) -> Dict[str, Any]:
    """Open an installed application through the execution safety gate."""
    return guarded_open_app(app_name)
