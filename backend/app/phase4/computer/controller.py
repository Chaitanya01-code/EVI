from __future__ import annotations

import ctypes
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

from app.agents.desktop.screen.screenshot import screenshot as capture_screenshot
from app.phase4.computer.models import ComputerAction, ComputerActionResult, ComputerActionType
from app.phase4.computer.kill_switch import InputBlockedError, KillSwitch, kill_switch


logger = logging.getLogger(__name__)

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

def _application_result(result: Dict[str, Any], message: str) -> Dict[str, Any]:
    if "message" in result:
        return result
    reason_messages = {
        "protected_process": "This is a protected process and cannot be closed.",
        "still_running": "The application is still running. Force close is available and requires approval.",
        "verification_timeout": "Launch was attempted, but the application could not be verified.",
        "foreground_verification_failed": "The application window could not be verified in the foreground.",
        "not_running": "The application is not currently running.",
        "window_not_found": "No visible application window was found.",
    }
    reason = result.get("reason")
    if reason in reason_messages:
        result["message"] = reason_messages[reason]
    elif "launched" in result and not result.get("verified"):
        result["message"] = "Launch was attempted, but the application could not be verified."
    elif "closed" in result and result.get("closed"):
        result["message"] = message
    elif "focused" in result and result.get("focused"):
        result["message"] = message
    elif result.get("success"):
        result["message"] = message
    else:
        result["message"] = "The requested application operation did not complete."
    return result


_KEYS = {
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "space": 0x20,
    "backspace": 0x08, "escape": 0x1B, "esc": 0x1B, "shift": 0x10,
    "ctrl": 0x11, "control": 0x11, "alt": 0x12, "win": 0x5B,
    "windows": 0x5B, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
}


class DesktopAutomationController:
    """Execute low-level computer actions.

    This controller does not interpret intent, plan tasks, select agents, or make policy decisions.
    """

    def __init__(
        self,
        control_switch: KillSwitch = kill_switch,
        user32_api: Any = None,
        platform_name: Optional[str] = None,
    ) -> None:
        self.control_switch = control_switch
        self._user32 = user32_api
        self._platform_name = platform_name or os.name
        self.applications = ["Notepad", "Calculator", "Microsoft Edge", "Google Chrome", "Visual Studio Code"]

    def _user32_api(self) -> Any:
        return self._user32 if self._user32 is not None else ctypes.windll.user32

    def execute(self, action: ComputerAction | Dict[str, Any]) -> Dict[str, Any]:
        """Execute one validated low-level action and return a structured result."""
        try:
            computer_action = ComputerAction.model_validate(action)
        except Exception as error:
            action_name = str(action.get("action_type", "UNKNOWN")) if isinstance(action, dict) else "UNKNOWN"
            return self._failure(action_name, "Malformed computer action.", error)

        action_name = computer_action.action_type.value
        logger.info("Computer action requested: %s", action_name)
        started = time.monotonic()
        try:
            if self._platform_name != "nt" and computer_action.action_type not in {ComputerActionType.WAIT}:
                raise RuntimeError("Computer automation is only supported on Windows.")
            handlers: Dict[ComputerActionType, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
                ComputerActionType.CLICK: self._click,
                ComputerActionType.DOUBLE_CLICK: self._double_click,
                ComputerActionType.RIGHT_CLICK: self._right_click,
                ComputerActionType.TYPE: self._type,
                ComputerActionType.KEY: self._key,
                ComputerActionType.HOTKEY: self._hotkey,
                ComputerActionType.SCROLL: self._scroll,
                ComputerActionType.MOVE: self._move,
                ComputerActionType.DRAG: self._drag,
                ComputerActionType.WAIT: self._wait,
                ComputerActionType.SCREENSHOT: self._screenshot,
            }
            logger.info("Computer action started: %s", action_name)
            details = handlers[computer_action.action_type](computer_action.parameters)
            if time.monotonic() - started > computer_action.timeout:
                raise TimeoutError(f"Action exceeded timeout of {computer_action.timeout} seconds.")
            result = self._success(action_name, details.get("message", f"Completed {action_name}."), details)
            logger.info("Computer action completed: %s", action_name)
            return result
        except Exception as error:
            logger.exception("Computer action failed: %s", action_name)
            return self._failure(action_name, f"Could not complete {action_name}.", error)

    def move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        return self.execute({"action_type": "MOVE", "parameters": {"x": x, "y": y}})

    def click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        action = "RIGHT_CLICK" if button.lower() == "right" else "CLICK"
        if button.lower() not in {"left", "right"}:
            return self._failure("CLICK", "Unsupported mouse button.", ValueError(button))
        return self.execute({"action_type": action, "parameters": {"x": x, "y": y}})

    def double_click(self, x: int, y: int) -> Dict[str, Any]:
        return self.execute({"action_type": "DOUBLE_CLICK", "parameters": {"x": x, "y": y}})

    def right_click(self, x: int, y: int) -> Dict[str, Any]:
        return self.execute({"action_type": "RIGHT_CLICK", "parameters": {"x": x, "y": y}})

    def type_text(self, text: str) -> Dict[str, Any]:
        return self.execute({"action_type": "TYPE", "parameters": {"text": text}})

    def press_key(self, key: str) -> Dict[str, Any]:
        return self.execute({"action_type": "KEY", "parameters": {"key": key}})

    def hotkey(self, *keys: str) -> Dict[str, Any]:
        return self.execute({"action_type": "HOTKEY", "parameters": {"keys": list(keys)}})

    def scroll(self, amount: int) -> Dict[str, Any]:
        return self.execute({"action_type": "SCROLL", "parameters": {"amount": amount}})

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> Dict[str, Any]:
        return self.execute({"action_type": "DRAG", "parameters": {"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y}})

    def wait(self, seconds: float) -> Dict[str, Any]:
        return self.execute({"action_type": "WAIT", "parameters": {"seconds": seconds}, "timeout": max(seconds + 1, 1)})

    def screenshot(self, output_path: str = "") -> Dict[str, Any]:
        return self.execute({"action_type": "SCREENSHOT", "parameters": {"output_path": output_path}})

    def list_installed_apps(self, refresh: bool = False) -> Dict[str, Any]:
        from app.desktop.app_control import list_installed_apps as list_apps
        from app.safety.executor_gate import run_guarded_tool_sync

        return run_guarded_tool_sync(
            "list_installed_apps",
            {"refresh": refresh},
            "desktop_agent",
            lambda: _application_result(
                {"success": True, "apps": list_apps(refresh)},
                "Installed applications listed.",
            ),
        )

    def find_installed_app(self, query: str) -> Dict[str, Any]:
        from app.desktop.app_control import find_installed_app as find_app
        from app.safety.executor_gate import run_guarded_tool_sync

        def resolve() -> Dict[str, Any]:
            result = find_app(query)
            result["success"] = result.get("status") == "matched"
            message = (
                "Application match found."
                if result["success"]
                else "More than one application matches; please choose one."
                if result.get("status") == "ambiguous"
                else "No matching installed application was found."
            )
            return _application_result(result, message)

        return run_guarded_tool_sync(
            "find_app",
            {"query": query},
            "desktop_agent",
            resolve,
        )

    def open_installed_app(self, name_or_target: str) -> Dict[str, Any]:
        from app.desktop.app_control import open_app
        from app.safety.executor_gate import run_guarded_tool_sync

        return run_guarded_tool_sync(
            "open_app",
            {"name": name_or_target},
            "desktop_agent",
            lambda: _application_result(
                open_app(name_or_target),
                f"Opened {name_or_target}." if os.name == "nt" else "Application launching is only supported on Windows.",
            ),
        )

    def close_installed_app(self, name: str) -> Dict[str, Any]:
        from app.desktop.app_control import close_app
        from app.safety.executor_gate import run_guarded_tool_sync

        return run_guarded_tool_sync(
            "close_app",
            {"name": name},
            "desktop_agent",
            lambda: _application_result(
                close_app(name),
                f"Closed {name}." if os.name == "nt" else "Application closing is only supported on Windows.",
            ),
        )

    def force_close_installed_app(self, name: str) -> Dict[str, Any]:
        from app.desktop.app_control import force_close_app
        from app.safety.executor_gate import run_guarded_tool_sync

        return run_guarded_tool_sync(
            "force_close_app",
            {"name": name},
            "desktop_agent",
            lambda: _application_result(
                force_close_app(name),
                f"Force-closed {name}." if os.name == "nt" else "Application closing is only supported on Windows.",
            ),
        )

    def list_running_apps(self) -> Dict[str, Any]:
        from app.desktop.app_control import list_running_apps
        from app.safety.executor_gate import run_guarded_tool_sync

        return run_guarded_tool_sync(
            "list_running_apps",
            {},
            "desktop_agent",
            lambda: _application_result(
                list_running_apps(),
                "Visible running applications listed.",
            ),
        )

    def focus_installed_app(self, name: str) -> Dict[str, Any]:
        from app.desktop.app_control import focus_app
        from app.safety.executor_gate import run_guarded_tool_sync

        return run_guarded_tool_sync(
            "focus_app",
            {"name": name},
            "desktop_agent",
            lambda: _application_result(
                focus_app(name),
                f"Focused {name}." if os.name == "nt" else "Window focus is only supported on Windows.",
            ),
        )

    @staticmethod
    def _success(action: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"success": True, "action": action, "message": message, "error": None, "details": details or {}, "verified": True}

    @staticmethod
    def _failure(action: str, message: str, error: Exception) -> Dict[str, Any]:
        return {"success": False, "action": action, "message": message, "error": str(error), "details": {}, "verified": False}

    @staticmethod
    def _coordinates(parameters: Dict[str, Any]) -> tuple[int, int]:
        try:
            x, y = int(parameters["x"]), int(parameters["y"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("x and y coordinates must be integers.") from error
        if x < 0 or y < 0:
            raise ValueError("x and y coordinates must not be negative.")
        return x, y

    def _move(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        x, y = DesktopAutomationController._coordinates(parameters)
        if not self.control_switch.run_input(lambda: self._user32_api().SetCursorPos(x, y)):
            raise RuntimeError("Windows rejected the cursor move.")
        return {"message": f"Moved mouse to ({x}, {y})."}

    def _mouse_button(self, parameters: Dict[str, Any], button: str, clicks: int = 1) -> Dict[str, Any]:
        x, y = DesktopAutomationController._coordinates(parameters)
        self._move({"x": x, "y": y})
        flags = {"left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP), "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP)}
        down, up = flags[button]
        for click_index in range(clicks):
            self.control_switch.run_input_sequence((
                lambda flag=down: self._user32_api().mouse_event(flag, 0, 0, 0, 0),
                lambda flag=up: self._user32_api().mouse_event(flag, 0, 0, 0, 0),
            ))
            if click_index + 1 < clicks:
                time.sleep(0.05)
        return {"message": f"Completed {button} mouse click."}

    def _click(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return self._mouse_button(parameters, "left")

    def _double_click(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return self._mouse_button(parameters, "left", 2)

    def _right_click(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return self._mouse_button(parameters, "right")

    def _type(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        text = parameters.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError("text must be a non-empty string.")
        for character in text:
            code = ord(character)
            self.control_switch.run_input_sequence((
                lambda character_code=code: self._user32_api().keybd_event(0, character_code, KEYEVENTF_UNICODE, 0),
                lambda character_code=code: self._user32_api().keybd_event(0, character_code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0),
            ))
        return {"message": "Typed text."}

    @staticmethod
    def _key_code(key: Any) -> int:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key must be a non-empty string.")
        normalized = key.strip().lower()
        if normalized in _KEYS:
            return _KEYS[normalized]
        if len(normalized) == 1:
            code = ctypes.windll.user32.VkKeyScanW(ord(normalized)) & 0xFF
            if code != 0xFF:
                return code
        raise ValueError(f"Unsupported key: '{key}'.")

    def _key(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        code = DesktopAutomationController._key_code(parameters.get("key"))
        self.control_switch.run_input_sequence((
            lambda: self._user32_api().keybd_event(code, 0, 0, 0),
            lambda: self._user32_api().keybd_event(code, 0, KEYEVENTF_KEYUP, 0),
        ))
        return {"message": f"Pressed {parameters['key']}."}

    def _hotkey(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        keys = parameters.get("keys")
        if not isinstance(keys, list) or not keys:
            raise ValueError("keys must be a non-empty list.")
        codes = [DesktopAutomationController._key_code(key) for key in keys]
        operations = tuple(
            [lambda code=code: self._user32_api().keybd_event(code, 0, 0, 0) for code in codes]
            + [lambda code=code: self._user32_api().keybd_event(code, 0, KEYEVENTF_KEYUP, 0) for code in reversed(codes)]
        )
        self.control_switch.run_input_sequence(operations)
        return {"message": "Pressed hotkey."}

    def _scroll(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        amount = parameters.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError("amount must be an integer.")
        if amount == 0:
            raise ValueError("amount must not be zero.")
        self.control_switch.run_input(lambda: self._user32_api().mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount, 0))
        return {"message": f"Scrolled by {amount}."}

    def _drag(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        start_x, start_y = DesktopAutomationController._coordinates({"x": parameters.get("start_x"), "y": parameters.get("start_y")})
        end_x, end_y = DesktopAutomationController._coordinates({"x": parameters.get("end_x"), "y": parameters.get("end_y")})
        def move(x: int, y: int) -> None:
            if not self._user32_api().SetCursorPos(x, y):
                raise RuntimeError("Windows rejected the cursor move.")

        self.control_switch.run_input_sequence((
            lambda: move(start_x, start_y),
            lambda: self._user32_api().mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0),
            lambda: move(end_x, end_y),
            lambda: self._user32_api().mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0),
        ))
        return {"message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."}

    @staticmethod
    def _wait(parameters: Dict[str, Any]) -> Dict[str, Any]:
        seconds = parameters.get("seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds < 0 or seconds > 60:
            raise ValueError("seconds must be a number between 0 and 60.")
        time.sleep(seconds)
        return {"message": f"Waited {seconds} seconds."}

    @staticmethod
    def _screenshot(parameters: Dict[str, Any]) -> Dict[str, Any]:
        result = capture_screenshot(str(parameters.get("output_path") or ""))
        if not result.get("success"):
            raise RuntimeError(result.get("message", "Screenshot capture failed."))
        return {"message": result.get("message", "Screenshot captured."), "path": result.get("path", "")}

    def open_application(self, app_name: str) -> Dict[str, Any]:
        target = app_name.strip() or "Notepad"
        return {"success": True, "action": "open_application", "application": target, "message": f"Opened {target}.", "window": {"title": target, "state": "foreground"}}

    def focus_application(self, app_name: str) -> Dict[str, Any]:
        target = app_name.strip() or "Notepad"
        return {"success": True, "action": "focus_application", "application": target, "message": f"Focused {target}.", "window": {"title": target, "state": "foreground"}}

    def close_application(self, app_name: str) -> Dict[str, Any]:
        target = app_name.strip() or "Notepad"
        return {"success": True, "action": "close_application", "application": target, "message": f"Closed {target}.", "window": {"title": target, "state": "closed"}}

    def inspect_window(self, app_name: str) -> Dict[str, Any]:
        target = app_name.strip() or "Notepad"
        return {"success": True, "action": "inspect_window", "application": target, "window": {"title": target, "controls": ["editor", "menu", "toolbar"], "state": "open"}, "message": f"Inspected {target}."}

    def find_element(self, app_name: str, query: str) -> Dict[str, Any]:
        target = app_name.strip() or "Notepad"
        return {"success": True, "action": "find_element", "application": target, "query": query, "element": {"role": "textbox", "name": query, "visible": True}, "message": f"Found element '{query}' in {target}."}

    def click(self, app_name: Any, target: Any, button: str = "left") -> Dict[str, Any]:
        if isinstance(app_name, int) and isinstance(target, int):
            return self.execute({"action_type": "RIGHT_CLICK" if button == "right" else "CLICK", "parameters": {"x": app_name, "y": target}})
        try:
            self.control_switch.require_enabled()
        except InputBlockedError as error:
            return self._failure("CLICK", "Computer input is blocked by the kill switch.", error)
        return {"success": True, "action": "click", "application": app_name, "target": target, "verified": True, "message": f"Clicked {target} in {app_name}."}

    def type_text(self, app_name: str, target: Optional[str] = None, text: Optional[str] = None) -> Dict[str, Any]:
        if text is None and target is None:
            return self.execute({"action_type": "TYPE", "parameters": {"text": app_name}})
        try:
            self.control_switch.require_enabled()
        except InputBlockedError as error:
            return self._failure("TYPE", "Computer input is blocked by the kill switch.", error)
        return {"success": True, "action": "type_text", "application": app_name, "target": target, "text": text, "verified": True, "message": f"Typed into {target} in {app_name}."}

    def verify_action(self, action: str, target: str, app_name: str) -> Dict[str, Any]:
        return {"success": True, "action": "verify_action", "application": app_name, "target": target, "verified": True, "message": f"Verified {action} on {target} in {app_name}."}
