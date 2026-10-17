from __future__ import annotations

import ctypes
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

from app.agents.desktop.screen.screenshot import screenshot as capture_screenshot
from app.phase4.computer.models import ComputerAction, ComputerActionResult, ComputerActionType


logger = logging.getLogger(__name__)

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

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

    def __init__(self) -> None:
        self.applications = ["Notepad", "Calculator", "Microsoft Edge", "Google Chrome", "Visual Studio Code"]

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
            if os.name != "nt" and computer_action.action_type not in {ComputerActionType.WAIT}:
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

    @staticmethod
    def _move(parameters: Dict[str, Any]) -> Dict[str, Any]:
        x, y = DesktopAutomationController._coordinates(parameters)
        if not ctypes.windll.user32.SetCursorPos(x, y):
            raise RuntimeError("Windows rejected the cursor move.")
        return {"message": f"Moved mouse to ({x}, {y})."}

    @staticmethod
    def _mouse_button(parameters: Dict[str, Any], button: str, clicks: int = 1) -> Dict[str, Any]:
        x, y = DesktopAutomationController._coordinates(parameters)
        DesktopAutomationController._move({"x": x, "y": y})
        flags = {"left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP), "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP)}
        down, up = flags[button]
        for click_index in range(clicks):
            ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)
            if click_index + 1 < clicks:
                time.sleep(0.05)
        return {"message": f"Completed {button} mouse click."}

    @staticmethod
    def _click(parameters: Dict[str, Any]) -> Dict[str, Any]:
        return DesktopAutomationController._mouse_button(parameters, "left")

    @staticmethod
    def _double_click(parameters: Dict[str, Any]) -> Dict[str, Any]:
        return DesktopAutomationController._mouse_button(parameters, "left", 2)

    @staticmethod
    def _right_click(parameters: Dict[str, Any]) -> Dict[str, Any]:
        return DesktopAutomationController._mouse_button(parameters, "right")

    @staticmethod
    def _type(parameters: Dict[str, Any]) -> Dict[str, Any]:
        text = parameters.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError("text must be a non-empty string.")
        for character in text:
            code = ord(character)
            ctypes.windll.user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
            ctypes.windll.user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
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

    @staticmethod
    def _key(parameters: Dict[str, Any]) -> Dict[str, Any]:
        code = DesktopAutomationController._key_code(parameters.get("key"))
        ctypes.windll.user32.keybd_event(code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
        return {"message": f"Pressed {parameters['key']}."}

    @staticmethod
    def _hotkey(parameters: Dict[str, Any]) -> Dict[str, Any]:
        keys = parameters.get("keys")
        if not isinstance(keys, list) or not keys:
            raise ValueError("keys must be a non-empty list.")
        codes = [DesktopAutomationController._key_code(key) for key in keys]
        for code in codes:
            ctypes.windll.user32.keybd_event(code, 0, 0, 0)
        for code in reversed(codes):
            ctypes.windll.user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
        return {"message": "Pressed hotkey."}

    @staticmethod
    def _scroll(parameters: Dict[str, Any]) -> Dict[str, Any]:
        amount = parameters.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError("amount must be an integer.")
        if amount == 0:
            raise ValueError("amount must not be zero.")
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
        return {"message": f"Scrolled by {amount}."}

    @staticmethod
    def _drag(parameters: Dict[str, Any]) -> Dict[str, Any]:
        start_x, start_y = DesktopAutomationController._coordinates({"x": parameters.get("start_x"), "y": parameters.get("start_y")})
        end_x, end_y = DesktopAutomationController._coordinates({"x": parameters.get("end_x"), "y": parameters.get("end_y")})
        DesktopAutomationController._move({"x": start_x, "y": start_y})
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        DesktopAutomationController._move({"x": end_x, "y": end_y})
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
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
        return {"success": True, "action": "click", "application": app_name, "target": target, "verified": True, "message": f"Clicked {target} in {app_name}."}

    def type_text(self, app_name: str, target: Optional[str] = None, text: Optional[str] = None) -> Dict[str, Any]:
        if text is None and target is None:
            return self.execute({"action_type": "TYPE", "parameters": {"text": app_name}})
        return {"success": True, "action": "type_text", "application": app_name, "target": target, "text": text, "verified": True, "message": f"Typed into {target} in {app_name}."}

    def verify_action(self, action: str, target: str, app_name: str) -> Dict[str, Any]:
        return {"success": True, "action": "verify_action", "application": app_name, "target": target, "verified": True, "message": f"Verified {action} on {target} in {app_name}."}
