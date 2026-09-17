from __future__ import annotations

import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

if sys.platform == "win32":
    import winreg
else:
    winreg = None  # type: ignore


@dataclass(frozen=True)
class Application:
    name: str
    command: str
    process_name: str = ""


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _candidate_start_menu_paths() -> Iterable[Path]:
    if os.name != "nt":
        return ()
    locations = (
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    )
    for location in locations:
        if location.exists():
            for path in location.rglob("*.lnk"):
                yield path


def _registry_app_paths() -> Iterable[tuple[str, str]]:
    """Query App Paths from Windows Registry (HKLM & HKCU) without hardcoding."""
    if winreg is None or os.name != "nt":
        return ()

    roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    sub_key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"

    for root in roots:
        try:
            with winreg.OpenKey(root, sub_key_path) as key:
                count_keys, _, _ = winreg.QueryInfoKey(key)
                for i in range(count_keys):
                    try:
                        app_sub_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, app_sub_name) as app_key:
                            exe_path, _ = winreg.QueryValueEx(app_key, "")
                            if exe_path and os.path.exists(exe_path):
                                base_name = Path(exe_path).stem
                                yield base_name, exe_path
                    except (OSError, EnvironmentError):
                        continue
        except (OSError, EnvironmentError):
            continue


def list_apps() -> List[Application]:
    """Dynamically discover user-launchable applications across Windows."""
    apps: Dict[str, Application] = {}

    # 1. Start Menu shortcuts
    for shortcut in _candidate_start_menu_paths():
        name = shortcut.stem
        norm = normalize_name(name)
        if norm and norm not in apps:
            apps[norm] = Application(name=name, command=str(shortcut), process_name=f"{shortcut.stem}.exe")

    # 2. Windows Registry App Paths (registered Windows applications)
    for name, exe_path in _registry_app_paths():
        norm = normalize_name(name)
        if norm and norm not in apps:
            proc_name = Path(exe_path).name
            apps[norm] = Application(name=name, command=exe_path, process_name=proc_name)

    # 3. Standard system executables discovered via PATH
    common_cli_candidates = (
        ("chrome", "Google Chrome", "chrome.exe"),
        ("code", "Visual Studio Code", "Code.exe"),
        ("notepad", "Notepad", "notepad.exe"),
        ("calc", "Calculator", "CalculatorApp.exe"),
        ("calculator", "Calculator", "CalculatorApp.exe"),
        ("explorer", "File Explorer", "explorer.exe"),
        ("spotify", "Spotify", "Spotify.exe"),
        ("discord", "Discord", "Discord.exe"),
        ("cmd", "Command Prompt", "cmd.exe"),
        ("powershell", "PowerShell", "powershell.exe"),
        ("msedge", "Microsoft Edge", "msedge.exe"),
    )
    for cmd_name, display_name, proc_name in common_cli_candidates:
        resolved = shutil.which(cmd_name) or shutil.which(f"{cmd_name}.exe")
        if resolved:
            norm = normalize_name(cmd_name)
            if norm not in apps:
                apps[norm] = Application(name=display_name, command=resolved, process_name=proc_name)

    return sorted(apps.values(), key=lambda app: app.name.lower())
