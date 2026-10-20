from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Union


PathResult = Union[Path, Dict[str, object]]


def _allowed_roots() -> list[Path]:
    home = Path.home()
    folder_names = ("Documents", "Desktop", "Downloads")
    roots = [home / name for name in folder_names]
    cloud_roots = {
        value for value in (
            os.getenv("OneDrive"),
            os.getenv("OneDriveCommercial"),
            os.getenv("OneDriveConsumer"),
        ) if value
    }
    for cloud_root in cloud_roots:
        roots.extend(Path(cloud_root) / name for name in folder_names)
    for value in os.getenv("EVI_ALLOWED_ROOTS", "").split(";"):
        if value.strip():
            roots.append(Path(os.path.expandvars(value.strip()).strip('"')).expanduser())
    resolved: list[Path] = []
    for root in roots:
        try:
            resolved.append(root.resolve(strict=False))
        except (OSError, RuntimeError):
            continue
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _denied(path: Path) -> bool:
    normalized = os.path.normcase(str(path)).replace("/", "\\").casefold()
    components = [part.casefold() for part in path.parts]
    if ".git" in components:
        return True
    if any(part in {"appdata", "programdata"} for part in components):
        return True
    name = path.name.casefold()
    if name == ".env" or name.startswith((".env.", "id_rsa")) or name.endswith((".pem", ".key")) or name.startswith("credentials"):
        return True
    denied_roots = (
        os.environ.get("WINDIR", r"C:\Windows"),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    )
    for denied_root in denied_roots:
        denied_normalized = os.path.normcase(denied_root).replace("/", "\\").rstrip("\\").casefold()
        if normalized == denied_normalized or normalized.startswith(denied_normalized + "\\"):
            return True
    return False


def resolve_safe(path: str | os.PathLike[str]) -> PathResult:
    """Expand and resolve a path, rejecting paths outside the user's allowed roots."""
    try:
        expanded = os.path.expandvars(os.path.expanduser(os.fspath(path)))
        if not expanded.strip():
            return {"ok": False, "reason": "outside_allowed_roots"}
        candidate = Path(expanded)
        if not candidate.is_absolute():
            parts = candidate.parts
            known = {"documents": Path.home() / "Documents", "desktop": Path.home() / "Desktop", "downloads": Path.home() / "Downloads"}
            base = known.get(parts[0].casefold(), Path.home() / "Documents")
            if parts[0].casefold() in known and not base.exists():
                cloud_roots = (
                    os.getenv("OneDrive"),
                    os.getenv("OneDriveCommercial"),
                    os.getenv("OneDriveConsumer"),
                )
                base = next(
                    (Path(root) / parts[0] for root in cloud_roots if root and (Path(root) / parts[0]).exists()),
                    base,
                )
            candidate = base.joinpath(*parts[1:]) if parts[0].casefold() in known else base / candidate
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError, TypeError, ValueError):
        return {"ok": False, "reason": "outside_allowed_roots"}

    if _denied(resolved):
        return {"ok": False, "reason": "denied_path"}

    roots = _allowed_roots()
    if not any(_is_relative_to(resolved, root) for root in roots):
        return {"ok": False, "reason": "outside_allowed_roots"}
    return resolved


def safe_path(path: str | os.PathLike[str]) -> tuple[Path | None, dict[str, object] | None]:
    result = resolve_safe(path)
    if isinstance(result, Path):
        return result, None
    return None, result
