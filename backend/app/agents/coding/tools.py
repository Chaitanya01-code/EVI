from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


_SAFE_COMMANDS = {"python", "python3", "py", "pytest", "git", "node", "npm", "pip", "pip3"}


def _result(success: bool, message: str, verified: bool = False, **data: Any) -> Dict[str, Any]:
    return {"success": success, "verified": verified, "message": message, **data}


def _root(path: str = "") -> Path:
    candidate = Path(path or os.getcwd()).expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(str(candidate))
    return candidate


def _resolve(path: str, working_directory: str = "") -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = _root(working_directory) / candidate
    return candidate.resolve()


def create_project(name: str, stack: str = "python", location: str = "") -> Dict[str, Any]:
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", name):
        return _result(False, "Project names may only contain letters, numbers, hyphens, and underscores.")
    base = _root(location or str(Path.home() / "Documents"))
    project = (base / name).resolve()
    if project.exists():
        return _result(False, f"The project directory already exists: {project}")
    project.mkdir()
    if stack.lower() in {"python", "fastapi"}:
        (project / "main.py").write_text('def main() -> None:\n    print("Hello from EVI")\n\n\nif __name__ == "__main__":\n    main()\n', encoding="utf-8")
        (project / "requirements.txt").write_text("", encoding="utf-8")
    return _result(True, f"Created the {stack} project at {project}.", True, path=str(project), stack=stack)


def inspect_project(path: str = "") -> Dict[str, Any]:
    root = _root(path)
    entries = sorted(str(item.relative_to(root)) for item in root.rglob("*") if ".git" not in item.parts)[:500]
    return _result(True, f"Inspected project {root}.", True, path=str(root), entries=entries)


def detect_stack(path: str = "") -> Dict[str, Any]:
    root = _root(path)
    markers = {"Python": ["pyproject.toml", "requirements.txt", "setup.py"], "Node": ["package.json"], "Rust": ["Cargo.toml"], "Go": ["go.mod"]}
    stacks = [name for name, files in markers.items() if any((root / file).exists() for file in files)]
    return _result(True, "Detected project technologies.", True, path=str(root), stacks=stacks)


def read_file(path: str, working_directory: str = "") -> Dict[str, Any]:
    file_path = _resolve(path, working_directory)
    if not file_path.is_file():
        return _result(False, f"I couldn't find {path}.", path=str(file_path), content="")
    return _result(True, f"Read {file_path.name}.", True, path=str(file_path), content=file_path.read_text(encoding="utf-8"))


def create_file(path: str, content: str, working_directory: str = "") -> Dict[str, Any]:
    file_path = _resolve(path, working_directory)
    if file_path.exists():
        return _result(False, f"The file already exists: {file_path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return _result(True, f"Created {file_path.name}.", file_path.is_file(), path=str(file_path))


def search_code(query: str, path: str = "") -> Dict[str, Any]:
    root = _root(path)
    matches: List[Dict[str, Any]] = []
    for file_path in root.rglob("*"):
        if not file_path.is_file() or ".git" in file_path.parts or file_path.stat().st_size > 1_000_000:
            continue
        try:
            for number, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
                if query.lower() in line.lower():
                    matches.append({"path": str(file_path), "line": number, "text": line.strip()})
        except (OSError, UnicodeDecodeError):
            continue
    return _result(True, f"Found {len(matches)} matches.", True, matches=matches[:200])


def run_command(command: str, working_directory: str = "", timeout: int = 30) -> Dict[str, Any]:
    if any(token in command for token in ("&", "|", ";", ">", "<", "$", "`")):
        return _result(False, "Shell chaining and redirection are not allowed by the Coding Agent policy.", command=command)
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = []
    lowered = command.lower()
    blocked = ("git push", "git reset", "git clean", "git checkout", "pip install", "npm install", "rm ", "del ", "rmdir")
    if not parts or Path(parts[0]).name.lower() not in _SAFE_COMMANDS or any(item in lowered for item in blocked):
        return _result(False, "That command is not allowed by the Coding Agent policy.", command=command)
    try:
        completed = subprocess.run(command, cwd=str(_root(working_directory)), shell=True, capture_output=True, text=True, timeout=min(timeout, 120), check=False)
        output = (completed.stdout + completed.stderr).strip()
        return _result(completed.returncode == 0, f"Command exited with code {completed.returncode}.", completed.returncode == 0, command=command, output=output, exit_code=completed.returncode)
    except (OSError, subprocess.SubprocessError) as error:
        return _result(False, f"I couldn't run that command: {error}", command=command, output="", exit_code=-1)


def run_tests(path: str = "") -> Dict[str, Any]:
    return run_command("python -m pytest", path, timeout=120)


def run_program(path: str, working_directory: str = "") -> Dict[str, Any]:
    if not path:
        return _result(False, "I need a program path to run.")
    program = Path(path)
    if program.is_dir():
        program = program / "main.py"
    return run_command(f'python "{program}"', working_directory or str(program.parent))


def git_status(path: str = "") -> Dict[str, Any]:
    return run_command("git status --short", path)


def git_diff(path: str = "") -> Dict[str, Any]:
    return run_command("git diff", path)


def detect_python() -> Dict[str, Any]:
    return _result(True, "Detected Python runtime.", True, executable=sys.executable, version=sys.version.split()[0])


def detect_node() -> Dict[str, Any]:
    executable = shutil.which("node")
    if not executable:
        return _result(False, "Node.js is not installed or not on PATH.")
    result = run_command("node --version")
    result["executable"] = executable
    return result


def unsupported(action: str) -> Dict[str, Any]:
    return _result(False, f"Coding action '{action}' requires an authorized edit/debug workflow and is not enabled yet.")
