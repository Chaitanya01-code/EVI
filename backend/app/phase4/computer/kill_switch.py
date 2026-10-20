from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Protocol, TypeVar


logger = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
HOTKEY_ID = 0x455649
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MODIFIERS = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
}
_KEYS = {
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "tab": 0x09,
    "pause": 0x13,
    "break": 0x03,
    "delete": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
}

T = TypeVar("T")


class ControlState(str, Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    STOPPED = "stopped"


class InputBlockedError(RuntimeError):
    pass


class HotkeyBackend(Protocol):
    def register_hotkey(self, modifiers: int, virtual_key: int) -> tuple[bool, str]: ...

    def hotkey_pressed(self) -> bool: ...

    def cursor_position(self) -> tuple[int, int]: ...

    def unregister_hotkey(self) -> None: ...


@dataclass(frozen=True)
class ParsedHotkey:
    label: str
    modifiers: int
    virtual_key: int


def parse_hotkey(value: str) -> ParsedHotkey:
    parts = [part.strip().lower() for part in value.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("EVI_STOP_HOTKEY must include a modifier and a key.")

    modifiers = 0
    key: Optional[int] = None
    key_name: Optional[str] = None
    for part in parts:
        if part in _MODIFIERS:
            bit = _MODIFIERS[part]
            if modifiers & bit:
                raise ValueError(f"Duplicate modifier in EVI_STOP_HOTKEY: {part}.")
            modifiers |= bit
            continue
        if key is not None:
            raise ValueError("EVI_STOP_HOTKEY must specify exactly one non-modifier key.")
        normalized = part.upper()
        if normalized.startswith("F") and normalized[1:].isdigit() and 1 <= int(normalized[1:]) <= 24:
            key = 0x70 + int(normalized[1:]) - 1
            key_name = normalized
        elif len(normalized) == 1 and normalized.isalnum():
            key = ord(normalized)
            key_name = normalized
        elif part in _KEYS:
            key = _KEYS[part]
            key_name = "Esc" if part in {"esc", "escape"} else part.title()
        else:
            raise ValueError(f"Unsupported key in EVI_STOP_HOTKEY: {part}.")
    if modifiers == 0 or key is None or key_name is None:
        raise ValueError("EVI_STOP_HOTKEY must include modifiers and exactly one key.")
    label = "+".join(
        [name for name, bit in (("Ctrl", MOD_CONTROL), ("Alt", MOD_ALT), ("Shift", MOD_SHIFT), ("Win", MOD_WIN)) if modifiers & bit]
        + [key_name]
    )
    return ParsedHotkey(label, modifiers, key)


class _Win32HotkeyBackend:
    def register_hotkey(self, modifiers: int, virtual_key: int) -> tuple[bool, str]:
        user32 = ctypes.windll.user32
        message = self._message_type()()
        user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        registered = bool(user32.RegisterHotKey(None, HOTKEY_ID, modifiers, virtual_key))
        if registered:
            return True, ""
        error_code = ctypes.get_last_error()
        return False, f"RegisterHotKey failed (Windows error {error_code})."

    def hotkey_pressed(self) -> bool:
        message = self._message_type()()
        user32 = ctypes.windll.user32
        while user32.PeekMessageW(ctypes.byref(message), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE):
            if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                return True
        return False

    @staticmethod
    def _message_type():
        from ctypes import wintypes

        class Point(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class Message(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", Point),
            ]

        return Message

    def cursor_position(self) -> tuple[int, int]:
        from ctypes import wintypes

        point = wintypes.POINT()
        if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
            raise OSError("GetCursorPos failed.")
        return point.x, point.y

    def unregister_hotkey(self) -> None:
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)


class KillSwitch:
    def __init__(
        self,
        hotkey_backend: Optional[HotkeyBackend] = None,
        platform_name: Optional[str] = None,
        hotkey: Optional[str] = None,
        corner_enabled: Optional[bool] = None,
        poll_interval: float = 0.05,
    ) -> None:
        self._lock = threading.RLock()
        self._listener_start_lock = threading.Lock()
        self._platform_name = platform_name or os.name
        self._backend = hotkey_backend or _Win32HotkeyBackend()
        self._hotkey_value = hotkey if hotkey is not None else os.getenv("EVI_STOP_HOTKEY", "Ctrl+Alt+Shift+Esc")
        self._corner_enabled = corner_enabled if corner_enabled is not None else os.getenv("EVI_STOP_CORNER_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
        self._poll_interval = poll_interval
        self._state = ControlState.DISABLED
        self._reason = "Computer control is disabled until explicitly enabled."
        self._registered = False
        self._listener_started = False
        self._listener_ready = threading.Event()
        self._shutdown_listener = threading.Event()
        self._listener_thread: Optional[threading.Thread] = None
        self._parsed_hotkey: Optional[ParsedHotkey] = None
        self._show_indicator: Optional[Callable[[], None]] = None
        self._hide_indicator: Optional[Callable[[], None]] = None
        self._corner_started_at: Optional[float] = None
        self._cancelled = threading.Event()

    def set_indicator(self, show: Callable[[], None], hide: Callable[[], None]) -> None:
        with self._lock:
            self._show_indicator = show
            self._hide_indicator = hide

    def start_listener(self, timeout: float = 3.0) -> bool:
        with self._listener_start_lock:
            if self._listener_started:
                self._refresh_listener_health()
                return self._registered and self._listener_thread is not None and self._listener_thread.is_alive()
            self._listener_started = True
            self._shutdown_listener.clear()
            try:
                if self._platform_name != "nt":
                    raise RuntimeError("The global stop hotkey is only supported on Windows.")
                self._parsed_hotkey = parse_hotkey(self._hotkey_value)
            except (RuntimeError, ValueError) as error:
                with self._lock:
                    self._reason = str(error)
                self._listener_ready.set()
                return False

            self._listener_thread = threading.Thread(
                target=self._listener_main,
                name="evi-computer-kill-switch",
                daemon=True,
            )
            self._listener_thread.start()
        if not self._listener_ready.wait(timeout):
            with self._lock:
                self._reason = "The global stop hotkey listener did not become ready in time."
            return False
        with self._lock:
            return self._registered and self._listener_thread is not None and self._listener_thread.is_alive()

    def _listener_main(self) -> None:
        registered = False
        failure_reported = False
        try:
            assert self._parsed_hotkey is not None
            registered, error = self._backend.register_hotkey(
                self._parsed_hotkey.modifiers,
                self._parsed_hotkey.virtual_key,
            )
            if not registered:
                with self._lock:
                    self._reason = error or "Windows refused to register the global stop hotkey."
                self._listener_ready.set()
                failure_reported = True
                return
            with self._lock:
                self._registered = True
                self._reason = "Computer control is disabled until explicitly enabled."
            self._listener_ready.set()

            while not self._shutdown_listener.wait(self._poll_interval):
                if self._backend.hotkey_pressed():
                    self.stop(f"Stopped by global hotkey ({self._parsed_hotkey.label}).")
                    continue
                with self._lock:
                    corner_monitoring = self._corner_enabled and self._state == ControlState.ENABLED
                if corner_monitoring:
                    x, y = self._backend.cursor_position()
                    if x <= 0 and y <= 0:
                        if self._corner_started_at is None:
                            self._corner_started_at = time.monotonic()
                        elif time.monotonic() - self._corner_started_at >= 0.5:
                            self.stop("Stopped by the top-left corner emergency stop.")
                            self._corner_started_at = None
                    else:
                        self._corner_started_at = None
                else:
                    self._corner_started_at = None
        except Exception as error:
            self._listener_failed(f"The global stop hotkey listener failed: {error}")
            failure_reported = True
        finally:
            if registered:
                try:
                    self._backend.unregister_hotkey()
                except Exception:
                    logger.exception("Unable to unregister EVI stop hotkey")
            if registered and not failure_reported and not self._shutdown_listener.is_set():
                self._listener_failed("The global stop hotkey listener exited unexpectedly.")
            self._listener_ready.set()

    def _listener_failed(self, reason: str) -> None:
        hide: Optional[Callable[[], None]] = None
        self._cancelled.set()
        with self._lock:
            self._registered = False
            self._reason = reason
            if self._state == ControlState.ENABLED:
                self._state = ControlState.STOPPED
                self._cancelled.set()
                hide = self._hide_indicator
        if hide:
            self._call_indicator(hide)

    def _refresh_listener_health(self) -> None:
        thread = self._listener_thread
        if self._listener_started and thread is not None and not thread.is_alive() and self._registered:
            self._listener_failed("The global stop hotkey listener stopped unexpectedly.")

    def status(self) -> dict[str, object]:
        self._refresh_listener_health()
        with self._lock:
            thread = self._listener_thread
            return {
                "state": self._state.value,
                "enabled": self._state == ControlState.ENABLED,
                "listener_registered": self._registered,
                "listener_alive": bool(thread and thread.is_alive()),
                "hotkey": self._parsed_hotkey.label if self._parsed_hotkey else self._hotkey_value,
                "corner_stop_enabled": self._corner_enabled,
                "reason": self._reason,
            }

    def enable(self) -> dict[str, object]:
        self._refresh_listener_health()
        with self._lock:
            if not self._registered or self._listener_thread is None or not self._listener_thread.is_alive():
                return self._status_locked()
            if self._state == ControlState.ENABLED:
                if self._cancelled.is_set():
                    self._state = ControlState.STOPPED
                    self._reason = "Computer control was stopped while re-enabling was requested."
                    if self._hide_indicator:
                        self._call_indicator(self._hide_indicator)
                    return self._status_locked()
                return self._status_locked()
            if self._show_indicator is None or self._hide_indicator is None:
                self._reason = "Computer control cannot be enabled because its visible stop indicator is unavailable."
                return self._status_locked()
            self._cancelled.clear()
            try:
                self._show_indicator()
            except Exception as error:
                self._reason = f"Computer control cannot be enabled because the visible indicator failed: {error}"
                self._call_indicator(self._hide_indicator)
                return self._status_locked()
            if not self._registered or not self._listener_thread.is_alive():
                self._call_indicator(self._hide_indicator)
                self._reason = "Computer control cannot be enabled because the stop listener is unavailable."
                return self._status_locked()
            if self._cancelled.is_set():
                self._state = ControlState.STOPPED
                self._reason = "Computer control was stopped while it was being enabled."
                self._call_indicator(self._hide_indicator)
                return self._status_locked()
            self._state = ControlState.ENABLED
            self._reason = "Computer control is enabled. Use the stop hotkey or visible Stop button to halt it."
            return self._status_locked()

    def stop(self, reason: str = "Computer control was stopped by the user.") -> dict[str, object]:
        hide: Optional[Callable[[], None]]
        self._cancelled.set()
        with self._lock:
            self._state = ControlState.STOPPED
            self._reason = reason
            self._cancelled.set()
            hide = self._hide_indicator
            status = self._status_locked()
        if hide:
            self._call_indicator(hide)
        return status

    def shutdown(self) -> None:
        self.stop("Computer control stopped during application shutdown.")
        self._shutdown_listener.set()
        thread = self._listener_thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def run_input(self, operation: Callable[[], T]) -> T:
        return self.run_input_sequence((operation,))[0]

    def require_enabled(self) -> None:
        self.run_input(lambda: None)

    def run_input_sequence(self, operations: tuple[Callable[[], T], ...]) -> tuple[T, ...]:
        results = []
        with self._lock:
            self._require_enabled_locked()
            # Keep press/release sequences atomic so a stop cannot strand a held key or button.
            for operation in operations:
                self._require_enabled_locked(check_cancelled=False)
                results.append(operation())
        return tuple(results)

    def _require_enabled_locked(self, check_cancelled: bool = True) -> None:
        thread = self._listener_thread
        if self._state == ControlState.ENABLED and (
            not self._registered or thread is None or not thread.is_alive()
        ):
            self._state = ControlState.STOPPED
            self._cancelled.set()
            self._reason = "Computer control stopped because the global stop listener is unavailable."
            if self._hide_indicator:
                self._call_indicator(self._hide_indicator)
        if self._state != ControlState.ENABLED or (check_cancelled and self._cancelled.is_set()):
            raise InputBlockedError(f"Computer input blocked by kill switch: {self._reason}")

    def _status_locked(self) -> dict[str, object]:
        thread = self._listener_thread
        return {
            "state": self._state.value,
            "enabled": self._state == ControlState.ENABLED,
            "listener_registered": self._registered,
            "listener_alive": bool(thread and thread.is_alive()),
            "hotkey": self._parsed_hotkey.label if self._parsed_hotkey else self._hotkey_value,
            "corner_stop_enabled": self._corner_enabled,
            "reason": self._reason,
        }

    @staticmethod
    def _call_indicator(callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception:
            logger.exception("Unable to update the EVI computer control indicator")


kill_switch = KillSwitch()
