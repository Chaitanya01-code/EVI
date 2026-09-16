from __future__ import annotations

import subprocess

from app.agents.desktop.applications.close_app import close_app
from app.agents.desktop.applications.find_app import find_app
from app.agents.desktop.applications.open_app import open_app
from app.agents.desktop.applications.restart_app import restart_app
from app.agents.desktop.registry import desktop_tools

__all__ = [
    "close_app",
    "desktop_tools",
    "find_app",
    "open_app",
    "restart_app",
]