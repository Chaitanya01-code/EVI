from __future__ import annotations

from typing import Any, Callable, Dict, Optional

# Applications
from app.agents.desktop.applications.close_app import close_app
from app.agents.desktop.applications.find_app import find_app
from app.agents.desktop.applications.list_apps import list_apps
from app.agents.desktop.applications.open_app import open_app
from app.agents.desktop.applications.restart_app import restart_app

# Windows
from app.agents.desktop.windows.maximize_window import maximize_window
from app.agents.desktop.windows.minimize_window import minimize_window
from app.agents.desktop.windows.move_window import move_window
from app.agents.desktop.windows.resize_window import resize_window
from app.agents.desktop.windows.switch_window import switch_window

# Files
from app.agents.desktop.files.copy_file import copy_file
from app.agents.desktop.files.delete_file import delete_file
from app.agents.desktop.files.move_file import move_file
from app.agents.desktop.files.open_file import open_file
from app.agents.desktop.files.rename_file import rename_file
from app.agents.desktop.files.search_file import search_file

# Folders
from app.agents.desktop.folders.create_folder import create_folder
from app.agents.desktop.folders.delete_folder import delete_folder
from app.agents.desktop.folders.move_folder import move_folder
from app.agents.desktop.folders.open_folder import open_folder
from app.agents.desktop.folders.rename_folder import rename_folder

# System
from app.agents.desktop.system.lock import lock
from app.agents.desktop.system.restart import restart
from app.agents.desktop.system.shutdown import shutdown
from app.agents.desktop.system.sleep import sleep

# Input
from app.agents.desktop.input.mouse_click import mouse_click
from app.agents.desktop.input.mouse_move import mouse_move
from app.agents.desktop.input.press_key import press_key
from app.agents.desktop.input.type_text import type_text

# Screen
from app.agents.desktop.screen.find_ui_element import find_ui_element
from app.agents.desktop.screen.inspect_screen import inspect_screen
from app.agents.desktop.screen.screenshot import screenshot

# Terminal
from app.agents.desktop.terminal.get_output import get_output
from app.agents.desktop.terminal.run_command import run_command
from app.agents.desktop.terminal.run_script import run_script


class DesktopToolRegistry:
    """Dedicated Desktop Tool Registry indexing all modular desktop capabilities."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Dict[str, Any]]] = {
            # Applications
            "applications.open_app": open_app,
            "applications.close_app": close_app,
            "applications.restart_app": restart_app,
            "applications.list_apps": list_apps,
            "applications.find_app": find_app,

            # Windows
            "windows.switch_window": switch_window,
            "windows.minimize_window": minimize_window,
            "windows.maximize_window": maximize_window,
            "windows.resize_window": resize_window,
            "windows.move_window": move_window,

            # Files
            "files.open_file": open_file,
            "files.copy_file": copy_file,
            "files.move_file": move_file,
            "files.rename_file": rename_file,
            "files.delete_file": delete_file,
            "files.search_file": search_file,

            # Folders
            "folders.create_folder": create_folder,
            "folders.open_folder": open_folder,
            "folders.rename_folder": rename_folder,
            "folders.move_folder": move_folder,
            "folders.delete_folder": delete_folder,

            # System
            "system.shutdown": shutdown,
            "system.restart": restart,
            "system.lock": lock,
            "system.sleep": sleep,

            # Input
            "input.mouse_click": mouse_click,
            "input.mouse_move": mouse_move,
            "input.type_text": type_text,
            "input.press_key": press_key,

            # Screen
            "screen.screenshot": screenshot,
            "screen.inspect_screen": inspect_screen,
            "screen.find_ui_element": find_ui_element,

            # Terminal
            "terminal.run_command": run_command,
            "terminal.run_script": run_script,
            "terminal.get_output": get_output,
        }

        # Shorthand / Legacy action aliases
        self._aliases: Dict[str, str] = {
            # Applications aliases
            "open_app": "applications.open_app",
            "open_application": "applications.open_app",
            "close_app": "applications.close_app",
            "close_application": "applications.close_app",
            "restart_app": "applications.restart_app",
            "restart_application": "applications.restart_app",
            "list_apps": "applications.list_apps",
            "find_app": "applications.find_app",

            # Windows aliases
            "switch_window": "windows.switch_window",
            "minimize_window": "windows.minimize_window",
            "maximize_window": "windows.maximize_window",
            "resize_window": "windows.resize_window",
            "move_window": "windows.move_window",

            # Files aliases
            "open_file": "files.open_file",
            "copy_file": "files.copy_file",
            "move_file": "files.move_file",
            "rename_file": "files.rename_file",
            "delete_file": "files.delete_file",
            "search_file": "files.search_file",

            # Folders aliases
            "create_folder": "folders.create_folder",
            "open_folder": "folders.open_folder",
            "rename_folder": "folders.rename_folder",
            "move_folder": "folders.move_folder",
            "delete_folder": "folders.delete_folder",

            # System aliases
            "shutdown": "system.shutdown",
            "restart": "system.restart",
            "lock": "system.lock",
            "sleep": "system.sleep",

            # Input aliases
            "mouse_click": "input.mouse_click",
            "mouse_move": "input.mouse_move",
            "type_text": "input.type_text",
            "press_key": "input.press_key",

            # Screen aliases
            "screenshot": "screen.screenshot",
            "inspect_screen": "screen.inspect_screen",
            "find_ui_element": "screen.find_ui_element",

            # Terminal aliases
            "run_command": "terminal.run_command",
            "run_script": "terminal.run_script",
            "get_output": "terminal.get_output",
        }

    def resolve(self, action: str) -> Optional[Callable[..., Dict[str, Any]]]:
        """Resolve an action name (e.g. 'applications.open_app' or 'open_app') to a callable tool."""
        if not action:
            return None
        if action in self._tools:
            return self._tools[action]
        aliased = self._aliases.get(action)
        if aliased and aliased in self._tools:
            return self._tools[aliased]
        return None

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())


desktop_tools = DesktopToolRegistry()