from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List


def search_file(filename: str, root_dir: str = "") -> Dict[str, Any]:
    """Search for a file by name. If ambiguous, returns clarification question."""
    if not filename:
        return {"success": False, "verified": False, "message": "No file name provided to search."}

    target = filename.strip().lower()
    search_roots = []
    if root_dir and os.path.isdir(root_dir):
        search_roots.append(Path(root_dir))
    else:
        user_home = Path.home()
        for folder in ("Documents", "Desktop", "Downloads", "Projects"):
            p = user_home / folder
            if p.exists():
                search_roots.append(p)
        search_roots.append(user_home)

    matches: List[str] = []
    seen = set()

    for root in search_roots:
        try:
            for dirpath, _, filenames in os.walk(root):
                # Avoid deep search into virtual environments, cache, or node_modules
                if any(ignored in dirpath for ignored in (".venv", "node_modules", ".git", "__pycache__")):
                    continue
                for f in filenames:
                    if f.lower() == target or target in f.lower():
                        full_path = os.path.join(dirpath, f)
                        if full_path not in seen:
                            seen.add(full_path)
                            matches.append(full_path)
                            if len(matches) >= 10:
                                break
                if len(matches) >= 10:
                    break
        except Exception:
            continue

    if not matches:
        return {"success": False, "verified": False, "message": f"I couldn't find any file matching '{filename}'."}

    if len(matches) > 1:
        match_list = "\n".join(f"- {p}" for p in matches[:5])
        return {
            "success": False,
            "verified": False,
            "ambiguous": True,
            "matches": matches,
            "message": f"I found multiple files matching that name. Which one do you mean?\n{match_list}",
        }

    return {
        "success": True,
        "verified": True,
        "path": matches[0],
        "message": f"Found {matches[0]}.",
    }
