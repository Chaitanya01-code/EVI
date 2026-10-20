from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

import psutil

from app.desktop.app_index import find_app, list_installed_apps, normalize_name


logger = logging.getLogger(__name__)
_PROTECTED_NAMES = {
    "explorer.exe", "csrss.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "svchost.exe", "system", "dwm.exe",
}


def _app_from_result(result: dict[str, Any]) -> Optional[dict[str, str]]:
    return result.get("app") if result.get("status") == "matched" else None


def _ambiguous_or_missing(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") == "ambiguous":
        return {
            "success": False,
            "verified": False,
            "reason": "ambiguous",
            "message": "More than one installed application matches. Please choose one.",
            "candidates": result.get("candidates", [])[:3],
        }
    return {
        "success": False,
        "verified": False,
        "reason": "not_found",
        "message": "No matching installed application was found.",
        "candidates": [],
    }


def _running_processes(app: dict[str, str]) -> list[psutil.Process]:
    expected_exe = (app.get("exe_name") or "").casefold()
    expected_path = os.path.normcase(app.get("launch_target") or "")
    expected_name = normalize_name(app["name"])
    matches = []
    for process in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            info = process.info
            proc_name = (info.get("name") or "").casefold()
            proc_exe = os.path.normcase(info.get("exe") or "")
            if expected_exe and proc_name == expected_exe:
                matches.append(process)
            elif expected_path and proc_exe == expected_path:
                matches.append(process)
            elif not expected_exe and expected_name and (
                expected_name in normalize_name(proc_name)
                or normalize_name(proc_name) in expected_name
            ):
                matches.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    if not expected_exe and app.get("source") == "uwp":
        matched_pids = {
            pid for _hwnd, pid, title in _window_rows()
            if normalize_name(app["name"]) in normalize_name(title)
        }
        known = {process.pid for process in matches}
        for pid in matched_pids - known:
            try:
                matches.append(psutil.Process(pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    return matches


def _window_rows() -> list[tuple[int, int, str]]:
    if os.name != "nt":
        return []
    try:
        import win32gui
        import win32process
    except ImportError:
        logger.warning("pywin32 is required to enumerate application windows")
        return []
    windows: list[tuple[int, int, str]] = []

    def collect(hwnd: int, _extra: Any) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return
        _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
        windows.append((hwnd, pid, title))

    try:
        win32gui.EnumWindows(collect, None)
    except Exception:
        logger.warning("Unable to enumerate application windows", exc_info=True)
    return windows


def _windows_for_processes(processes: list[psutil.Process]) -> list[tuple[int, int, str]]:
    pids = {process.pid for process in processes}
    return [row for row in _window_rows() if row[1] in pids]


def _protected_pids() -> set[int]:
    protected: set[int] = set()
    try:
        current = psutil.Process(os.getpid())
        protected.add(current.pid)
        protected.update(process.pid for process in current.parents())
        protected.update(process.pid for process in current.children(recursive=True))
    except (psutil.Error, OSError):
        logger.warning("Unable to enumerate EVI process ancestry for protection", exc_info=True)
        protected.add(os.getpid())
    return protected


def _is_protected(process: psutil.Process) -> bool:
    if process.pid in _protected_pids():
        return True
    try:
        name = (process.name() or "").casefold()
        return name in _PROTECTED_NAMES
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return True


def _resolve_app(query: str) -> tuple[Optional[dict[str, str]], Optional[dict[str, Any]]]:
    result = find_app(query)
    app = _app_from_result(result)
    return app, None if app else _ambiguous_or_missing(result)


def open_app(name_or_target: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"success": False, "launched": False, "verified": False, "pids": [], "window_title": "", "reason": "windows_only"}
    requested_path = Path(name_or_target)
    app: Optional[dict[str, str]] = None
    failure: Optional[dict[str, Any]] = None
    if requested_path.is_file() and requested_path.suffix.lower() in {".lnk", ".exe"}:
        app = {
            "name": requested_path.stem,
            "source": "lnk" if requested_path.suffix.lower() == ".lnk" else "registry",
            "launch_target": str(requested_path),
            "exe_name": "",
            "install_location": "",
        }
    else:
        app, failure = _resolve_app(name_or_target)
    if app is None:
        return {"success": False, "launched": False, "verified": False, "pids": [], "window_title": "", **(failure or {})}

    before = {process.pid for process in _running_processes(app)}
    target = app["launch_target"]
    try:
        if target.startswith("shell:AppsFolder\\"):
            subprocess.Popen(
                ["explorer.exe", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        else:
            os.startfile(target)
    except (OSError, subprocess.SubprocessError, AttributeError) as error:
        return {
            "success": False,
            "launched": False,
            "verified": False,
            "pids": [],
            "window_title": "",
            "reason": "launch_failed",
            "message": str(error),
            "app": app["name"],
        }

    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        processes = _running_processes(app)
        new_processes = [process for process in processes if process.pid not in before]
        windows = _windows_for_processes(processes)
        verified = bool(new_processes or windows)
        if verified:
            pids = sorted({process.pid for process in processes})
            return {
                "success": True,
                "launched": True,
                "verified": True,
                "pids": pids,
                "window_title": windows[0][2] if windows else "",
                "app": app["name"],
            }
        time.sleep(0.25)
    return {
        "success": False,
        "launched": True,
        "verified": False,
        "pids": [],
        "window_title": "",
        "reason": "verification_timeout",
        "app": app["name"],
    }


def _request_close(process: psutil.Process) -> None:
    try:
        import win32con
        import win32gui

        for hwnd, pid, _title in _windows_for_processes([process]):
            if pid == process.pid:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    except ImportError:
        logger.warning("pywin32 is required to close application windows gracefully")


def close_app(name: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"success": False, "closed": False, "reason": "windows_only"}
    app, failure = _resolve_app(name)
    if app is None:
        return {"success": False, "closed": False, **(failure or {})}
    processes = _running_processes(app)
    if not processes:
        return {"success": True, "closed": True, "verified": True, "pids": [], "app": app["name"]}
    if any(_is_protected(process) for process in processes):
        return {"success": False, "closed": False, "reason": "protected_process", "app": app["name"]}

    for process in processes:
        _request_close(process)
    _, alive = psutil.wait_procs(processes, timeout=5)
    if alive:
        return {
            "success": False,
            "closed": False,
            "verified": False,
            "reason": "still_running",
            "pids": [process.pid for process in alive],
            "app": app["name"],
            "force_close_available": True,
        }
    return {"success": True, "closed": True, "verified": True, "pids": [], "app": app["name"]}


def force_close_app(name: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"success": False, "closed": False, "reason": "windows_only"}
    app, failure = _resolve_app(name)
    if app is None:
        return {"success": False, "closed": False, **(failure or {})}
    processes = _running_processes(app)
    if not processes:
        return {"success": True, "closed": True, "verified": True, "pids": [], "app": app["name"]}
    if any(_is_protected(process) for process in processes):
        return {"success": False, "closed": False, "reason": "protected_process", "app": app["name"]}
    for process in processes:
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _, alive = psutil.wait_procs(processes, timeout=3)
    for process in alive:
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _, alive = psutil.wait_procs(processes, timeout=2)
    return {
        "success": not alive,
        "closed": not alive,
        "verified": not alive,
        "reason": "still_running" if alive else None,
        "pids": [process.pid for process in alive],
        "app": app["name"],
    }


def list_running_apps() -> dict[str, Any]:
    windows = _window_rows()
    apps = []
    seen: set[tuple[int, str]] = set()
    for _hwnd, pid, title in windows:
        if (pid, title) in seen:
            continue
        seen.add((pid, title))
        try:
            process = psutil.Process(pid)
            apps.append({
                "name": process.name(),
                "pid": pid,
                "window_title": title,
                "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return {"success": True, "apps": apps}


def focus_app(name: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"success": False, "focused": False, "verified": False, "reason": "windows_only"}
    app, failure = _resolve_app(name)
    if app is None:
        return {"success": False, "focused": False, "verified": False, **(failure or {})}
    processes = _running_processes(app)
    if not processes:
        return {"success": False, "focused": False, "verified": False, "reason": "not_running", "app": app["name"]}
    windows = _windows_for_processes(processes)
    if not windows:
        return {"success": False, "focused": False, "verified": False, "reason": "window_not_found", "app": app["name"]}
    try:
        import win32con
        import win32gui

        hwnd, pid, title = windows[0]
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        foreground = win32gui.GetForegroundWindow()
        verified = foreground == hwnd
        return {
            "success": verified,
            "focused": verified,
            "verified": verified,
            "pid": pid,
            "window_title": title,
            "app": app["name"],
            "reason": None if verified else "foreground_verification_failed",
        }
    except Exception as error:
        logger.warning("Unable to focus application window", exc_info=True)
        return {"success": False, "focused": False, "verified": False, "reason": str(error), "app": app["name"]}


def find_installed_app(query: str) -> dict[str, Any]:
    result = find_app(query)
    result["success"] = result["status"] == "matched"
    return result
