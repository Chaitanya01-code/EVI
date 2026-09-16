from __future__ import annotations

import sys
from typing import List, Optional, Tuple

if sys.platform == "win32":
    try:
        import win32con
        import win32gui
        import win32process
    except ImportError:
        win32gui = None
        win32con = None
        win32process = None
else:
    win32gui = None
    win32con = None
    win32process = None


def get_visible_windows() -> List[Tuple[int, str]]:
    """Return a list of (hwnd, title) for all currently visible desktop windows."""
    if win32gui is None:
        return []

    windows: List[Tuple[int, str]] = []

    def enum_handler(hwnd: int, extra: None) -> None:
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title and not win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOOLWINDOW:
                windows.append((hwnd, title))

    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        pass
    return windows


def find_window_by_target(target: str) -> Optional[Tuple[int, str]]:
    """Find a window hwnd matching a target query (e.g. 'Chrome', 'Visual Studio Code', 'Notepad')."""
    if not target or win32gui is None:
        return None

    target_norm = target.strip().lower()
    windows = get_visible_windows()

    # Exact match on title
    for hwnd, title in windows:
        if title.lower() == target_norm:
            return hwnd, title

    # Substring match on title
    for hwnd, title in windows:
        if target_norm in title.lower():
            return hwnd, title

    # Word boundary match (e.g. "code" in "VS Code" or "Chrome" in "Google Chrome")
    alias_map = {
        "vs code": "visual studio code",
        "code": "visual studio code",
        "chrome": "google chrome",
        "calc": "calculator",
    }
    alias = alias_map.get(target_norm, target_norm)
    for hwnd, title in windows:
        if alias in title.lower():
            return hwnd, title

    return None
