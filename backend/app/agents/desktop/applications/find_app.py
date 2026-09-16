from __future__ import annotations

import shutil
from typing import Optional

from app.agents.desktop import applications
from app.agents.desktop.applications.list_apps import Application, normalize_name

_KNOWN_ALIASES = {
    "vs code": "visual studio code",
    "vscode": "visual studio code",
    "code": "visual studio code",
    "google chrome": "chrome",
    "calc": "calculator",
    "file explorer": "explorer",
    "files": "explorer",
}


def find_app(app_name: str) -> Optional[Application]:
    """Resolve an application query against discoverable Windows applications."""
    if not app_name:
        return None

    normalized_query = normalize_name(app_name)
    if not normalized_query:
        return None

    # Resolve alias if present
    normalized_query = _KNOWN_ALIASES.get(normalized_query, normalized_query)

    all_apps = applications.list_apps()

    # 1. Exact match on normalized name
    for app in all_apps:
        if normalize_name(app.name) == normalized_query:
            return app

    # 2. Match if query is contained in app name or vice versa
    for app in all_apps:
        norm_app = normalize_name(app.name)
        if normalized_query in norm_app or norm_app in normalized_query:
            return app

    # 3. Match against executable/command name
    for app in all_apps:
        cmd_stem = normalize_name(app.command.split("\\")[-1].replace(".exe", "").replace(".lnk", ""))
        if cmd_stem and (normalized_query == cmd_stem or normalized_query in cmd_stem):
            return app

    # 4. Direct PATH resolution fallback for arbitrary installed executables
    candidate = shutil.which(app_name) or shutil.which(f"{app_name}.exe")
    if candidate:
        return Application(name=app_name, command=candidate, process_name=f"{app_name}.exe")

    return None
