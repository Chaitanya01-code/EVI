from __future__ import annotations

import threading
import time
from typing import Optional
from unittest.mock import Mock

import pytest

from app.phase4.computer.controller import DesktopAutomationController
from app.phase4.computer.kill_switch import ControlState, KillSwitch, parse_hotkey


class FakeHotkeyBackend:
    def __init__(self, register_result: tuple[bool, str] = (True, "")) -> None:
        self.register_result = register_result
        self.registered = threading.Event()
        self.hotkey = threading.Event()
        self.fail_listener = threading.Event()
        self.unregister_called = threading.Event()
        self.cursor = (100, 100)

    def register_hotkey(self, modifiers: int, virtual_key: int) -> tuple[bool, str]:
        self.registered.set()
        return self.register_result

    def hotkey_pressed(self) -> bool:
        if self.fail_listener.is_set():
            raise RuntimeError("simulated listener failure")
        return self.hotkey.is_set()

    def cursor_position(self) -> tuple[int, int]:
        return self.cursor

    def unregister_hotkey(self) -> None:
        self.unregister_called.set()


def _new_switch(
    backend: Optional[FakeHotkeyBackend] = None,
    corner_enabled: bool = False,
) -> tuple[KillSwitch, FakeHotkeyBackend]:
    hotkey_backend = backend or FakeHotkeyBackend()
    switch = KillSwitch(
        hotkey_backend=hotkey_backend,
        platform_name="nt",
        corner_enabled=corner_enabled,
        poll_interval=0.005,
    )
    switch.set_indicator(lambda: None, lambda: None)
    assert switch.start_listener()
    return switch, hotkey_backend


def _controller(switch: KillSwitch, user32: Optional[Mock] = None) -> DesktopAutomationController:
    api = user32 or Mock()
    api.SetCursorPos.return_value = 1
    return DesktopAutomationController(switch, user32_api=api, platform_name="nt")


def _wait_for_state(switch: KillSwitch, expected: ControlState, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if switch.status()["state"] == expected.value:
            return
        time.sleep(0.005)
    raise AssertionError(f"Expected state {expected.value}; got {switch.status()}")


def test_starts_disabled_and_blocks_every_controller_input_path():
    switch, _ = _new_switch()
    try:
        assert switch.status()["state"] == ControlState.DISABLED.value
        user32 = Mock()
        user32.SetCursorPos.return_value = 1
        controller = _controller(switch, user32)
        actions = (
            {"action_type": "MOVE", "parameters": {"x": 10, "y": 20}},
            {"action_type": "CLICK", "parameters": {"x": 10, "y": 20}},
            {"action_type": "DOUBLE_CLICK", "parameters": {"x": 10, "y": 20}},
            {"action_type": "RIGHT_CLICK", "parameters": {"x": 10, "y": 20}},
            {"action_type": "TYPE", "parameters": {"text": "no"}},
            {"action_type": "KEY", "parameters": {"key": "enter"}},
            {"action_type": "HOTKEY", "parameters": {"keys": ["ctrl", "a"]}},
            {"action_type": "SCROLL", "parameters": {"amount": 120}},
            {"action_type": "DRAG", "parameters": {"start_x": 1, "start_y": 2, "end_x": 3, "end_y": 4}},
        )

        results = [controller.execute(action) for action in actions]

        assert all(not result["success"] for result in results)
        assert all("kill switch" in result["error"].lower() for result in results)
        user32.SetCursorPos.assert_not_called()
        user32.mouse_event.assert_not_called()
        user32.keybd_event.assert_not_called()
        assert not controller.click("Notepad", "button")["success"]
        assert not controller.type_text("Notepad", "editor", "text")["success"]
    finally:
        switch.shutdown()


def test_enabled_controller_emits_input_and_stop_blocks_later_paths():
    switch, backend = _new_switch()
    try:
        assert switch.enable()["enabled"]
        user32 = Mock()
        user32.SetCursorPos.return_value = 1
        controller = _controller(switch, user32)
        assert controller.type_text("ok")["success"]
        assert controller.move_mouse(10, 20)["success"]
        assert controller.click(10, 20)["success"]
        assert controller.press_key("enter")["success"]
        assert user32.keybd_event.call_count == 6
        assert user32.SetCursorPos.called
        assert user32.mouse_event.called

        backend.hotkey.set()
        _wait_for_state(switch, ControlState.STOPPED)
        call_counts = (
            user32.SetCursorPos.call_count,
            user32.mouse_event.call_count,
            user32.keybd_event.call_count,
        )
        actions = (
            {"action_type": "MOVE", "parameters": {"x": 10, "y": 20}},
            {"action_type": "CLICK", "parameters": {"x": 10, "y": 20}},
            {"action_type": "DOUBLE_CLICK", "parameters": {"x": 10, "y": 20}},
            {"action_type": "RIGHT_CLICK", "parameters": {"x": 10, "y": 20}},
            {"action_type": "TYPE", "parameters": {"text": "no"}},
            {"action_type": "KEY", "parameters": {"key": "enter"}},
            {"action_type": "HOTKEY", "parameters": {"keys": ["ctrl", "a"]}},
            {"action_type": "SCROLL", "parameters": {"amount": 120}},
            {"action_type": "DRAG", "parameters": {"start_x": 1, "start_y": 2, "end_x": 3, "end_y": 4}},
        )
        results = [controller.execute(action) for action in actions]
        assert all(not result["success"] for result in results)
        assert all("kill switch" in result["error"].lower() for result in results)
        assert not controller.click("Notepad", "button")["success"]
        assert not controller.type_text("Notepad", "editor", "text")["success"]
        assert call_counts == (
            user32.SetCursorPos.call_count,
            user32.mouse_event.call_count,
            user32.keybd_event.call_count,
        )
    finally:
        switch.shutdown()


def test_stop_cancels_in_flight_typing_and_blocks_remaining_characters():
    switch, _ = _new_switch()
    try:
        assert switch.enable()["enabled"]
        user32 = Mock()
        user32.SetCursorPos.return_value = 1
        first_event = threading.Event()

        def slow_key_event(*_args):
            if not first_event.is_set():
                first_event.set()
                time.sleep(0.05)

        user32.keybd_event.side_effect = slow_key_event
        controller = _controller(switch, user32)
        result_holder = {}
        worker = threading.Thread(
            target=lambda: result_holder.setdefault(
                "result",
                controller.execute({"action_type": "TYPE", "parameters": {"text": "abc"}}),
            )
        )
        worker.start()
        assert first_event.wait(0.5)
        stop_thread = threading.Thread(target=switch.stop)
        stop_thread.start()
        stop_thread.join(timeout=1)
        worker.join(timeout=1)

        assert not worker.is_alive()
        assert not stop_thread.is_alive()
        assert result_holder["result"]["success"] is False
        assert user32.keybd_event.call_count == 2
        assert switch.status()["state"] == ControlState.STOPPED.value
    finally:
        switch.shutdown()


def test_hotkey_registration_failure_keeps_control_blocked():
    backend = FakeHotkeyBackend((False, "hotkey already registered"))
    switch = KillSwitch(backend, platform_name="nt", corner_enabled=False)
    switch.set_indicator(lambda: None, lambda: None)
    try:
        assert not switch.start_listener()
        status = switch.status()
        assert status["state"] == ControlState.DISABLED.value
        assert not status["listener_registered"]
        assert "already registered" in status["reason"]
        assert not switch.enable()["enabled"]
        with pytest.raises(RuntimeError, match="kill switch"):
            switch.require_enabled()
    finally:
        switch.shutdown()


def test_listener_death_stops_enabled_control_and_blocks_input():
    switch, backend = _new_switch()
    try:
        assert switch.enable()["enabled"]
        backend.fail_listener.set()
        _wait_for_state(switch, ControlState.STOPPED)
        status = switch.status()
        assert not status["listener_registered"]
        assert "listener failed" in status["reason"].lower()
        with pytest.raises(RuntimeError, match="kill switch"):
            switch.require_enabled()
    finally:
        switch.shutdown()


def test_stop_remains_stopped_until_explicit_reenable():
    switch, backend = _new_switch()
    try:
        assert switch.enable()["enabled"]
        backend.hotkey.set()
        _wait_for_state(switch, ControlState.STOPPED)
        backend.hotkey.clear()
        with pytest.raises(RuntimeError, match="kill switch"):
            switch.require_enabled()
        assert switch.status()["state"] == ControlState.STOPPED.value

        assert switch.enable()["enabled"]
        assert switch.status()["state"] == ControlState.ENABLED.value
    finally:
        switch.shutdown()


def test_lab_health_exposes_kill_switch_status(monkeypatch):
    from app.api import lab_schemas
    from app.api.routes.lab import routes

    class Status:
        def status(self):
            return {
                "state": "disabled",
                "enabled": False,
                "listener_registered": True,
                "listener_alive": True,
                "hotkey": "Ctrl+Alt+Shift+Esc",
                "corner_stop_enabled": False,
                "reason": "disabled",
            }

    monkeypatch.setattr(routes, "kill_switch", Status())
    monkeypatch.setattr(routes, "get_connection", lambda: _fake_connection())
    response = routes.health()
    validated = lab_schemas.HealthResponse.model_validate(response)
    assert validated.kill_switch["state"] == "disabled"
    assert validated.components["computer_control"] == "disabled"


def test_computer_control_api_routes_are_registered():
    from app.main import app

    paths = app.openapi()["paths"]
    assert "get" in paths["/api/computer/control/status"]
    assert "post" in paths["/api/computer/control/enable"]
    assert "post" in paths["/api/computer/control/stop"]


def test_computer_control_api_delegates_to_shared_switch(monkeypatch):
    from fastapi import HTTPException

    from app import main

    class FakeSwitch:
        def status(self):
            return {"state": "disabled", "enabled": False}

        def enable(self):
            return {"state": "enabled", "enabled": True}

        def stop(self, reason):
            return {"state": "stopped", "enabled": False, "reason": reason}

    fake = FakeSwitch()
    monkeypatch.setattr(main, "kill_switch", fake)
    assert main.computer_control_status() == {"state": "disabled", "enabled": False}
    assert main.computer_control_enable()["enabled"]
    assert main.computer_control_stop()["state"] == "stopped"

    fake.enable = lambda: {"state": "disabled", "enabled": False, "reason": "listener failed"}
    with pytest.raises(HTTPException) as error:
        main.computer_control_enable()
    assert error.value.status_code == 503
    assert error.value.detail["reason"] == "listener failed"


def test_top_left_corner_stop_is_available_when_enabled():
    backend = FakeHotkeyBackend()
    backend.cursor = (0, 0)
    switch, _ = _new_switch(backend, corner_enabled=True)
    try:
        assert switch.enable()["enabled"]
        _wait_for_state(switch, ControlState.STOPPED, timeout=1.5)
        assert "top-left corner" in switch.status()["reason"]
    finally:
        switch.shutdown()


def test_indicator_failure_prevents_enable():
    switch, _ = _new_switch()
    switch.set_indicator(
        lambda: (_ for _ in ()).throw(RuntimeError("tk unavailable")),
        lambda: None,
    )
    try:
        status = switch.enable()
        assert not status["enabled"]
        assert status["state"] == ControlState.DISABLED.value
        assert "indicator failed" in status["reason"]
    finally:
        switch.shutdown()


def test_hotkey_environment_syntax_is_parsed_generically():
    parsed = parse_hotkey("Ctrl+Alt+Shift+Esc")
    assert parsed.label == "Ctrl+Alt+Shift+Esc"
    with pytest.raises(ValueError, match="exactly one"):
        parse_hotkey("Ctrl+Alt+Esc+F1")


class _fake_connection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, *_args):
        return None
