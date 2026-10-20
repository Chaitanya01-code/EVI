from __future__ import annotations

from typing import Any

from app.phase4.computer.controller import DesktopAutomationController


_controller = DesktopAutomationController()


def list_installed_apps(refresh: bool = False) -> dict[str, Any]:
    return _controller.list_installed_apps(refresh)


def find_app(query: str) -> dict[str, Any]:
    return _controller.find_installed_app(query)


def open_app(name_or_target: str) -> dict[str, Any]:
    return _controller.open_installed_app(name_or_target)


def close_app(name: str) -> dict[str, Any]:
    return _controller.close_installed_app(name)


def force_close_app(name: str) -> dict[str, Any]:
    return _controller.force_close_installed_app(name)


def list_running_apps() -> dict[str, Any]:
    return _controller.list_running_apps()


def focus_app(name: str) -> dict[str, Any]:
    return _controller.focus_installed_app(name)
