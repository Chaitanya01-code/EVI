from __future__ import annotations

from typing import Any, Dict

from app.agents.desktop.applications.installed_apps import close_app as guarded_close_app


def close_app(app_name: str) -> Dict[str, Any]:
    """Gracefully close an installed application through the execution safety gate."""
    return guarded_close_app(app_name)
