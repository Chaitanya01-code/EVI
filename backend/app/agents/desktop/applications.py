from __future__ import annotations

from app.agents.desktop.applications.close_app import close_app
from app.agents.desktop.applications.find_app import find_app
from app.agents.desktop.applications.list_apps import Application, list_apps, normalize_name
from app.agents.desktop.applications.open_app import open_app
from app.agents.desktop.applications.restart_app import restart_app

__all__ = [
    "Application",
    "close_app",
    "find_app",
    "list_apps",
    "normalize_name",
    "open_app",
    "restart_app",
]