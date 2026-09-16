from __future__ import annotations

from typing import Any, Callable, Dict

from app.agents.coding.tools import (
    create_file, create_project, detect_node, detect_python, detect_stack, run_program,
    git_diff, git_status, inspect_project, read_file, run_command, run_tests,
    search_code, unsupported,
)


class CodingToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Dict[str, Any]]] = {
            "create_project": create_project,
            "inspect_project": inspect_project,
            "detect_stack": detect_stack,
            "read_file": read_file,
            "create_file": create_file,
            "search_code": search_code,
            "run_command": run_command,
            "run_program": run_program,
            "run_script": run_command,
            "run_tests": run_tests,
            "git_status": git_status,
            "status": git_status,
            "git_diff": git_diff,
            "diff": git_diff,
            "detect_python": detect_python,
            "detect_node": detect_node,
            "install_dependency": lambda **_: unsupported("install_dependency"),
            "edit_file": lambda **_: unsupported("edit_file"),
            "delete_file": lambda **_: unsupported("delete_file"),
            "commit": lambda **_: unsupported("commit"),
            "push": lambda **_: unsupported("push"),
        }

    def resolve(self, action: str) -> Callable[..., Dict[str, Any]] | None:
        return self._tools.get(action)


coding_tools = CodingToolRegistry()
