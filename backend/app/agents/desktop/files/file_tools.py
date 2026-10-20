from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from app.desktop import file_operations as operations
from app.safety.executor_gate import run_guarded_sync


def _execute(
    tool: str,
    params: dict[str, Any],
    run: Callable[[], dict[str, Any]],
    risk: str | None = None,
    *,
    skip_approval: bool = False,
) -> dict[str, Any]:
    action: dict[str, Any] = {"tool": tool, "params": params}
    if risk:
        action["risk"] = risk
    gated = run_guarded_sync(action, "desktop_agent", run, _skip_approval=skip_approval)
    if gated.get("status") == "ok":
        result = gated.get("result")
        if isinstance(result, dict):
            result.setdefault("message", result.get("reason") or "File operation completed.")
            return result
        return {"ok": True, "success": True, "verified": True, "message": str(result), "result": result}
    response: dict[str, Any] = {
        "ok": False,
        "success": False,
        "verified": False,
        "status": gated.get("status"),
        "reason": gated.get("status"),
        "message": gated.get("summary") or gated.get("error") or gated.get("status"),
    }
    if gated.get("approval_id"):
        response["approval_id"] = gated["approval_id"]
    return response


def list_dir(path: str, depth: int = 1) -> dict[str, Any]:
    return _execute("list_dir", {"path": path, "depth": depth}, lambda: operations.list_dir(path, depth))


def search_files(root: str, name_glob: str = "*", extension: str = "", modified_after: str = "", limit: int = 200) -> dict[str, Any]:
    params = {"root": root, "name_glob": name_glob, "extension": extension, "modified_after": modified_after, "limit": limit}
    return _execute("search_files", params, lambda: operations.search_files(root, name_glob, extension, modified_after, limit))


def search_in_files(root: str, text: str, extensions: list[str] | None = None, limit: int = 200) -> dict[str, Any]:
    params = {"root": root, "text": text, "extensions": extensions or [], "limit": limit}
    return _execute("search_in_files", params, lambda: operations.search_in_files(root, text, extensions, limit))


def file_info(path: str) -> dict[str, Any]:
    return _execute("file_info", {"path": path}, lambda: operations.file_info(path))


def read_file(path: str, max_chars: int = 20000) -> dict[str, Any]:
    return _execute("read_file", {"path": path, "max_chars": max_chars}, lambda: operations.read_file(path, max_chars))


def create_folder(path: str = "", location: str = "", folder_name: str = "") -> dict[str, Any]:
    if folder_name:
        path = folder_name
    if location:
        return create_folder_legacy(path, location)
    return _execute("create_folder", {"path": path}, lambda: operations.create_folder(path))


def create_file(path: str, content: str) -> dict[str, Any]:
    return _execute("create_file", {"path": path, "content": content}, lambda: operations.create_file(path, content))


def write_file(path: str, content: str, mode: str = "overwrite", overwrite: bool = False) -> dict[str, Any]:
    risk = "high" if overwrite else None
    params = {"path": path, "content": content, "mode": mode, "overwrite": overwrite}
    return _execute("write_file", params, lambda: operations.write_file(path, content, mode, overwrite), risk)


def create_docx(path: str, title: str, paragraphs: list[str]) -> dict[str, Any]:
    params = {"path": path, "title": title, "paragraphs": paragraphs}
    return _execute("create_docx", params, lambda: operations.create_docx(path, title, paragraphs))


def create_xlsx(path: str, rows: list[list[Any]]) -> dict[str, Any]:
    params = {"path": path, "rows": rows}
    return _execute("create_xlsx", params, lambda: operations.create_xlsx(path, rows))


def copy_file(source: str, destination: str, overwrite: bool = False) -> dict[str, Any]:
    risk = "high" if overwrite else None
    params = {"src": source, "dst": destination, "overwrite": overwrite}
    preview = _folder_preview("copy", source, destination, overwrite)
    if preview and not preview.get("ok"):
        return _execute("copy_file", params, lambda: preview, risk, skip_approval=True)
    result = _execute("copy_file", params, lambda: operations.copy(source, destination, overwrite), risk)
    if result.get("status") == "needs_approval" and preview:
        result.update({"planned": preview["planned"], "count": preview["count"]})
    return result


def copy(src: str, dst: str, overwrite: bool = False) -> dict[str, Any]:
    return copy_file(src, dst, overwrite)


def move_file(source: str, destination: str, overwrite: bool = False) -> dict[str, Any]:
    params = {"src": source, "dst": destination, "overwrite": overwrite}
    preview = _folder_preview("move", source, destination, overwrite)
    if preview and not preview.get("ok"):
        return _execute("move_file", params, lambda: preview, "high", skip_approval=True)
    result = _execute("move_file", params, lambda: operations.move(source, destination, overwrite), "high")
    if result.get("status") == "needs_approval" and preview:
        result.update({"planned": preview["planned"], "count": preview["count"]})
    return result


def move(src: str, dst: str, overwrite: bool = False) -> dict[str, Any]:
    return move_file(src, dst, overwrite)


def _folder_preview(op: str, source: str, destination: str, overwrite: bool) -> dict[str, Any] | None:
    src, error = operations._guard(source)
    if error or src is None or not src.is_dir():
        return None
    dst, error = operations._guard(destination)
    if error or dst is None:
        return {"ok": False, "success": False, "verified": False, **(error or {"reason": "invalid_destination"})}
    target_root = dst / src.name if dst.exists() and dst.is_dir() else dst
    planned = [{"op": op, "src": str(src), "dst": str(target_root)}]
    for item in src.rglob("*"):
        if len(planned) >= 200:
            return {"ok": False, "success": False, "verified": False, "reason": "limit_exceeded", "limit": 200}
        safe_item, item_error = operations._guard(item)
        if item_error or safe_item is None:
            return {"ok": False, "success": False, "verified": False, **(item_error or {"reason": "denied_path"})}
        relative = item.relative_to(src)
        dest_item, dest_error = operations._guard(target_root / relative)
        if dest_error or dest_item is None:
            return {"ok": False, "success": False, "verified": False, **(dest_error or {"reason": "outside_allowed_roots"})}
        if dest_item.exists() and not overwrite:
            return {"ok": False, "success": False, "verified": False, "reason": "exists", "path": str(dest_item)}
        planned.append({"op": op, "src": str(safe_item), "dst": str(dest_item)})
    if len(planned) <= 1:
        return None
    return {"ok": True, "planned": planned, "count": len(planned)}


def rename_file(source: str, destination: str) -> dict[str, Any]:
    source_path = Path(source)
    target = destination if Path(destination).is_absolute() else str(source_path.parent / destination)
    return _execute("rename_file", {"src": source, "dst": target}, lambda: operations.move(source, target), "high")


def move_folder(source: str, destination: str) -> dict[str, Any]:
    preview = _folder_preview("move", source, destination, False)
    if preview and not preview.get("ok"):
        return _execute("move_folder", {"src": source, "dst": destination}, lambda: preview, "high", skip_approval=True)
    result = _execute("move_folder", {"src": source, "dst": destination}, lambda: operations.move(source, destination), "high")
    if result.get("status") == "needs_approval" and preview:
        result.update({"planned": preview["planned"], "count": preview["count"]})
    return result


def rename_folder(source: str, destination: str) -> dict[str, Any]:
    source_path = Path(source)
    target = destination if Path(destination).is_absolute() else str(source_path.parent / destination)
    preview = _folder_preview("rename", source, target, False)
    params = {"src": source, "dst": target}
    if preview and not preview.get("ok"):
        return _execute("rename_folder", params, lambda: preview, "high", skip_approval=True)
    result = _execute("rename_folder", params, lambda: operations.move(source, target), "high")
    if result.get("status") == "needs_approval" and preview:
        result.update({"planned": preview["planned"], "count": preview["count"]})
    return result


def delete_file(file_path: str) -> dict[str, Any]:
    preview: dict[str, Any] = {}
    resolved, _error = operations._guard(file_path)
    too_many = False
    if resolved is not None and resolved.is_dir():
        children = []
        for path in resolved.rglob("*"):
            children.append(path)
            if len(children) > 200:
                too_many = True
                break
        guarded = [str(path) for path in children if operations._guard(path)[1] is None]
        if guarded:
            preview = {"planned": [{"op": "delete", "src": str(resolved), "dst": ""}], "count": len(guarded) + 1}
    if too_many:
        result = _execute(
            "delete_file",
            {"path": file_path},
            lambda: {"ok": False, "success": False, "verified": False, "reason": "limit_exceeded", "limit": 200},
            "high",
            skip_approval=True,
        )
    else:
        result = _execute("delete_file", {"path": file_path}, lambda: operations.delete(file_path), "high")
    if result.get("status") == "needs_approval" and preview:
        result.update(preview)
    return result


def delete(path: str) -> dict[str, Any]:
    return delete_file(path)


def delete_folder(folder_path: str) -> dict[str, Any]:
    return delete_file(folder_path)


def open_file(file_path: str) -> dict[str, Any]:
    return _execute("open_file", {"path": file_path}, lambda: operations.open_file(file_path))


def open_in_explorer(path: str) -> dict[str, Any]:
    return _execute("open_in_explorer", {"path": path}, lambda: operations.open_in_explorer(path))


def open_folder(folder_path: str) -> dict[str, Any]:
    return open_in_explorer(folder_path)


def search_file(filename: str, root_dir: str = "") -> dict[str, Any]:
    return _execute(
        "search_file",
        {"filename": filename, "root_dir": root_dir},
        lambda: _search_file_result(filename, root_dir),
    )


def bulk_file_operation(
    op: str = "",
    root: str = "",
    pattern: str = "",
    destination: str = "",
    source: str = "",
    target: str = "",
) -> dict[str, Any]:
    if not (op and root and pattern) and (source or target):
        request = f"{target} {source} {destination}".strip()
        match = re.search(
            r"\b(copy|move|delete|rename)\s+(?:all\s+)?(.+?)\s+from\s+(.+?)(?:\s+to\s+(.+))?$",
            request,
            flags=re.IGNORECASE,
        )
        if match:
            op = match.group(1).casefold()
            pattern = match.group(2).strip().strip("'\"")
            root = match.group(3).strip().strip("'\"")
            destination = (match.group(4) or "").strip().strip("'\"")
    if op not in {"copy", "move", "delete", "rename"} or not (root and pattern):
        invalid = {"ok": False, "success": False, "verified": False, "reason": "invalid_bulk_request"}
        return _execute(
            "bulk_file_operation",
            {"op": op, "root": root, "pattern": pattern, "destination": destination},
            lambda: invalid,
            "high",
            skip_approval=True,
        )
    if pattern and "*" not in pattern and "?" not in pattern and "." not in pattern:
        stem = pattern[:-1] if pattern.casefold().endswith("s") else pattern
        pattern = f"*{stem}*"
    preview = operations.plan_bulk(op, root, pattern, destination)
    if not preview.get("ok"):
        return _execute(
            "bulk_file_operation",
            {"op": op, "root": root, "pattern": pattern, "destination": destination},
            lambda: preview,
            "high",
            skip_approval=True,
        )
    if preview["count"] == 0:
        return preview
    params = {"op": op, "root": root, "pattern": pattern, "destination": destination, "planned": preview["planned"]}
    gated = run_guarded_sync(
        {"tool": f"bulk_{op}", "params": params, "risk": "high"},
        "desktop_agent",
        lambda: operations.execute_bulk(preview),
    )
    if gated.get("status") == "ok":
        result = gated.get("result")
        return result if isinstance(result, dict) else {"ok": True, "success": True, "verified": True}
    response = {
        "ok": False,
        "success": False,
        "verified": False,
        "status": gated.get("status"),
        "reason": gated.get("status"),
        "message": gated.get("summary") or gated.get("error") or gated.get("status"),
        "planned": preview["planned"],
        "count": preview["count"],
    }
    if gated.get("approval_id"):
        response["approval_id"] = gated["approval_id"]
    return response


def create_folder_legacy(folder_name: str, location: str = "") -> dict[str, Any]:
    if not folder_name:
        return {"ok": False, "success": False, "verified": False, "reason": "missing_name"}
    base = Path(location).expanduser() if location else Path.home() / "Documents"
    if not base.is_absolute():
        known = {"desktop": Path.home() / "Desktop", "documents": Path.home() / "Documents", "downloads": Path.home() / "Downloads"}
        base = known.get(location.casefold(), Path.home() / "Documents" / location)
    return create_folder(str(base / folder_name))


def _search_file_result(filename: str, root_dir: str = "") -> dict[str, Any]:
    roots = [root_dir] if root_dir else [
        str(Path.home() / name) for name in ("Documents", "Desktop", "Downloads")
    ]
    matches = []
    for search_root in roots:
        result = operations.search_files(search_root, f"*{filename}*", limit=10)
        matches.extend(row["path"] for row in result.get("matches", []))
        if len(matches) >= 10:
            break
    matches = list(dict.fromkeys(matches))[:10]
    if matches:
        if len(matches) == 1:
            return {"ok": True, "success": True, "verified": True, "path": matches[0], "message": f"Found {matches[0]}."}
        return {"ok": True, "success": False, "verified": True, "ambiguous": True, "matches": matches, "message": "Multiple matching files were found."}
    return {"ok": True, "success": False, "verified": True, "matches": [], "message": f"No file matching {filename!r} was found."}


def legacy_search_file(filename: str, root_dir: str = "") -> dict[str, Any]:
    return search_file(filename, root_dir)
