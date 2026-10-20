from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from rapidfuzz import fuzz, process

try:
    import winreg
except ImportError:
    winreg = None


logger = logging.getLogger(__name__)
APP_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "app_index.json"
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60

_ALIASES = {
    "chrome": "google chrome",
    "google chrome": "google chrome",
    "vs code": "visual studio code",
    "vscode": "visual studio code",
    "code": "visual studio code",
    "word": "microsoft word",
    "excel": "microsoft excel",
    "notepad": "notepad",
    "calc": "calculator",
    "calculator": "calculator",
    "cmd": "command prompt",
}
_SKIP_WORDS = ("uninstall", "uninstaller", "documentation", "readme", "help")
_SOURCE_PRIORITY = {"lnk": 0, "uwp": 1, "registry": 2}
_REGISTRY_LOCATIONS = (
    (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0),
    (r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", 0),
    (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0x0100),
)


@dataclass(frozen=True)
class AppEntry:
    name: str
    source: str
    launch_target: str
    exe_name: str = ""
    install_location: str = ""


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _should_skip(name: str) -> bool:
    normalized = normalize_name(name)
    return not normalized or any(word in normalized for word in _SKIP_WORDS)


def _shortcut_target(shortcut: Path) -> str:
    if os.name != "nt":
        return ""
    try:
        from win32com.client import Dispatch

        return str(Dispatch("WScript.Shell").CreateShortCut(str(shortcut)).Targetpath or "")
    except Exception:
        logger.debug("Unable to resolve shortcut target: %s", shortcut, exc_info=True)
        return ""


def _start_menu_entries() -> list[AppEntry]:
    if os.name != "nt":
        return []
    roots = (
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    )
    entries = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            shortcuts = root.rglob("*.lnk")
            for shortcut in shortcuts:
                name = shortcut.stem
                if _should_skip(name):
                    continue
                target = _shortcut_target(shortcut)
                entries.append(AppEntry(
                    name=name,
                    source="lnk",
                    launch_target=str(shortcut),
                    exe_name=Path(target).name if target else "",
                ))
        except OSError:
            logger.warning("Unable to scan Start Menu folder %s", root, exc_info=True)
    return entries


def _registry_executable(install_location: str, display_icon: str) -> tuple[str, str]:
    icon = display_icon.strip().strip('"')
    icon = re.sub(r",\s*-?\d+$", "", icon)
    if icon and Path(icon).is_file() and Path(icon).suffix.lower() == ".exe":
        return icon, Path(icon).name
    location = Path(install_location.strip().strip('"')) if install_location.strip() else None
    if location and location.is_file() and location.suffix.lower() == ".exe":
        return str(location), location.name
    if location and location.is_dir():
        try:
            executables = sorted(
                location.glob("*.exe"),
                key=lambda path: (path.name.casefold().startswith(("unins", "setup")), path.name.casefold()),
            )
        except OSError:
            executables = []
        for executable in executables:
            if not _should_skip(executable.stem):
                return str(executable), executable.name
    return "", ""


def _registry_entries() -> list[AppEntry]:
    if os.name != "nt" or winreg is None:
        return []
    roots = ((winreg.HKEY_LOCAL_MACHINE, "HKLM"), (winreg.HKEY_CURRENT_USER, "HKCU"))
    entries: list[AppEntry] = []
    for root, _root_name in roots:
        for subkey, view in _REGISTRY_LOCATIONS:
            try:
                with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | view) as uninstall_key:
                    count = winreg.QueryInfoKey(uninstall_key)[0]
                    for index in range(count):
                        try:
                            child_name = winreg.EnumKey(uninstall_key, index)
                            with winreg.OpenKey(uninstall_key, child_name) as app_key:
                                try:
                                    display_name = str(winreg.QueryValueEx(app_key, "DisplayName")[0]).strip()
                                except OSError:
                                    continue
                                if _should_skip(display_name):
                                    continue
                                try:
                                    install_location = str(winreg.QueryValueEx(app_key, "InstallLocation")[0] or "").strip()
                                except OSError:
                                    install_location = ""
                                try:
                                    display_icon = str(winreg.QueryValueEx(app_key, "DisplayIcon")[0] or "").strip()
                                except OSError:
                                    display_icon = ""
                                exe_path, exe_name = _registry_executable(install_location, display_icon)
                                if exe_path and Path(exe_path).suffix.lower() == ".exe":
                                    entries.append(AppEntry(
                                        name=display_name,
                                        source="registry",
                                        launch_target=exe_path,
                                        exe_name=exe_name,
                                        install_location=install_location,
                                    ))
                        except OSError:
                            continue
            except OSError:
                continue
    return entries


def _uwp_entries() -> list[AppEntry]:
    if os.name != "nt":
        return []
    script = (
        "Get-StartApps | Select-Object Name,AppID | "
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("Unable to query Windows Start Apps", exc_info=True)
        return []
    if completed.returncode != 0:
        logger.warning("Get-StartApps failed: %s", completed.stderr[:300])
        return []
    try:
        raw = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        logger.warning("Get-StartApps returned invalid JSON")
        return []
    if isinstance(raw, dict):
        raw = [raw]
    entries = []
    for row in raw if isinstance(raw, list) else []:
        name = str(row.get("Name") or "").strip()
        app_id = str(row.get("AppID") or "").strip()
        if name and app_id and not _should_skip(name):
            entries.append(AppEntry(
                name=name,
                source="uwp",
                launch_target=f"shell:AppsFolder\\{app_id}",
            ))
    return entries


def _build_index() -> list[AppEntry]:
    by_name: dict[str, AppEntry] = {}
    entries = [*_start_menu_entries(), *_uwp_entries(), *_registry_entries()]
    for entry in entries:
        key = normalize_name(entry.name)
        if not key:
            continue
        previous = by_name.get(key)
        if previous is None or _SOURCE_PRIORITY[entry.source] < _SOURCE_PRIORITY[previous.source]:
            by_name[key] = entry
    return sorted(by_name.values(), key=lambda entry: normalize_name(entry.name))


def list_installed_apps(refresh: bool = False) -> list[dict[str, str]]:
    """Return a cached installed-app index, refreshing it at most every 24 hours."""
    if not refresh:
        try:
            cached = json.loads(APP_INDEX_PATH.read_text(encoding="utf-8"))
            age = time.time() - float(cached["timestamp"])
            if 0 <= age < CACHE_MAX_AGE_SECONDS:
                return cached["apps"]
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass
    apps = [asdict(entry) for entry in _build_index()]
    payload = {"timestamp": time.time(), "apps": apps}
    try:
        APP_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = APP_INDEX_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(APP_INDEX_PATH)
    except OSError:
        logger.warning("Unable to cache installed-app index", exc_info=True)
    return apps


def _resolve_query(query: str) -> tuple[Optional[dict[str, str]], list[dict[str, Any]]]:
    normalized_query = normalize_name(query)
    normalized_query = _ALIASES.get(normalized_query, normalized_query)
    apps = list_installed_apps()
    choices: dict[str, dict[str, str]] = {}
    for app in apps:
        choices.setdefault(normalize_name(app["name"]), app)
    ranked = process.extract(
        normalized_query,
        list(choices),
        scorer=fuzz.WRatio,
        limit=3,
    )
    candidates = [
        {"app": choices[normalized], "score": score}
        for normalized, score, _index in ranked
    ]
    if candidates and candidates[0]["score"] >= 90:
        next_score = candidates[1]["score"] if len(candidates) > 1 else 0
        if candidates[0]["score"] - next_score >= 10:
            return candidates[0]["app"], candidates
    return None, candidates


def find_app(query: str) -> dict[str, Any]:
    if not query.strip():
        return {"status": "not_found", "app": None, "candidates": []}
    app, candidates = _resolve_query(query)
    if app:
        return {"status": "matched", "app": app, "candidates": candidates}
    return {"status": "ambiguous" if candidates else "not_found", "app": None, "candidates": candidates}
