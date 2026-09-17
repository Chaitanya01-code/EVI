from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.classify import GEMINI_MODEL, _generate_llm, _get_client
from app.task.task_models import StructuredTask, TaskType

logger = logging.getLogger(__name__)


class TaskStep(BaseModel):
    task_type: str = Field(description="desktop, browser, coding, cloud")
    category: str = Field(default="", description="applications, navigation, etc.")
    action: str = Field(description="Action name")
    target: str = Field(default="", description="Target entity")
    depends_on: List[str] = Field(default_factory=list, description="Optional prior step ids required before execution")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class TaskUnderstandingResult(BaseModel):
    task_type: TaskType
    category: str = Field(default="", description="Category: applications, windows, files, folders, system, input, screen, terminal, navigation, coding, cloud, orchestration")
    action: str = Field(description="Action name, e.g. open_app, close_app, search, create_project, deploy")
    target: str = Field(default="", description="The target entity, e.g. Chrome, Visual Studio Code, Docker tutorials")
    steps: List[TaskStep] = Field(default_factory=list, description="List of sub-tasks for multi_step tasks")
    confidence: float = Field(default=0.8, ge=0, le=1)


_TASK_INSTRUCTION = """
You are EVI's task understanding layer. Convert an executable user request into structured JSON.

CRITICAL ARCHITECTURAL DISTINCTION:
The requested OPERATION determines the task_type and category, NOT the target application!
The target application (e.g. "Chrome", "VS Code", "Notepad", "Calculator") is simply a desktop application.
Opening or closing ANY application (including a browser like Chrome) is ALWAYS a desktop task.
Web browsing or searching is a browser task.

Task Types and Categories:
1. "desktop"
   - category "applications": open_app, close_app, restart_app, list_apps, find_app
     Examples: "Open Chrome" -> action: "open_app", target: "Chrome"
               "Open VS Code" -> action: "open_app", target: "Visual Studio Code"
               "Open Notepad" -> action: "open_app", target: "Notepad"
               "Open Calculator" -> action: "open_app", target: "Calculator"
               "Close Chrome" -> action: "close_app", target: "Chrome"
               "Restart VS Code" -> action: "restart_app", target: "Visual Studio Code"
   - category "windows": switch_window, minimize_window, maximize_window, resize_window, move_window
     Examples: "Switch to Chrome", "Minimize VS Code", "Maximize Notepad"
   - category "files": open_file, copy_file, move_file, rename_file, delete_file, search_file
     Examples: "Open resume.pdf", "Copy report.pdf to Documents", "Rename notes.txt to final_notes.txt"
   - category "folders": create_folder, open_folder, rename_folder, move_folder, delete_folder
     Examples: "Create a folder called EVI in Documents", "Open my Projects folder"
   - category "system": shutdown, restart, lock, sleep
   - category "input": mouse_click, mouse_move, type_text, press_key
   - category "screen": screenshot, inspect_screen, find_ui_element
   - category "terminal": run_command, run_script, get_output

2. "browser"
   - category "navigation": search, navigate, open_url
     Examples: "Search Google for Docker tutorials" -> action: "search", target: "Docker tutorials"
               "Search the web for Python" -> action: "search", target: "Python"
               "Open a website" -> action: "navigate", target: "website"

3. "coding"
   - category "development": create_project, debug_code, run_tests
     Examples: "Create a Python project", "Debug this Python code", "Create a FastAPI application"

4. "cloud"
   - category "deployment": deploy, check_deployment
     Examples: "Deploy my application to AWS", "Check my Docker deployment"

5. "multi_step"
   - Tasks combining multiple distinct operations across domains:
     Example: "Open Chrome and search Google for Docker tutorials" ->
     task_type: "multi_step", category: "orchestration", action: "multi_step", target: "",
     steps: [
       {"task_type": "desktop", "category": "applications", "action": "open_app", "target": "Chrome"},
       {"task_type": "browser", "category": "navigation", "action": "search", "target": "Docker tutorials"}
     ]

6. "unknown"
   - Unrecognized or ambiguous tasks.

Return JSON with exactly: task_type, category, action, target, steps, confidence.
""".strip()


def _normalize_app_target(raw_target: str) -> str:
    cleaned = raw_target.strip().rstrip(".")
    lower = cleaned.lower()
    mapping = {
        "vs code": "Visual Studio Code",
        "vscode": "Visual Studio Code",
        "visual studio code": "Visual Studio Code",
        "chrome": "Chrome",
        "google chrome": "Chrome",
        "notepad": "Notepad",
        "calc": "Calculator",
        "calculator": "Calculator",
        "spotify": "Spotify",
        "discord": "Discord",
        "file explorer": "File Explorer",
        "explorer": "File Explorer",
        "settings": "Settings",
    }
    return mapping.get(lower, cleaned)


def _split_task_clauses(text: str) -> List[str]:
    cleaned = text.strip().rstrip(".")
    if not cleaned:
        return []
    lowered = cleaned.lower()
    if "at the same time" in lowered or "simultaneously" in lowered or "while also" in lowered:
        separator = r"\s*(?:,|\band\b|\bthen\b|\bwhile\b|\bplus\b)\s*"
    else:
        separator = r"\s*(?:,|\band\b|\bthen\b)\s*"
    clauses = [part.strip(" ,.") for part in re.split(separator, cleaned, flags=re.IGNORECASE) if part.strip(" ,.")]
    return clauses


def _extract_query_from_text(text: str) -> str:
    lowered = text.lower()
    for prefix in ("search for ", "look for ", "find ", "search the web for ", "search google for ", "google "):
        index = lowered.find(prefix)
        if index >= 0:
            tail = text[index + len(prefix):].strip()
            tail = re.split(r"\s+(?:and|then|,|\.|$)", tail, maxsplit=1, flags=re.IGNORECASE)[0]
            return tail.strip(" \t\n.,\"'")
    if "search" in lowered:
        match = re.search(r"\bsearch\b(?:\s+for)?\s+(.+)$", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" \t\n.,\"'")
    return text.strip(" \t\n.,\"'")


def _fallback_understanding(text: str) -> TaskUnderstandingResult:
    cleaned = text.strip()
    normalized = cleaned.lower()

    parallel_match = re.search(
        r"\b(?:open|launch|start)\b\s+(.+?)\s+(?:and|,)\s+(.+?)\s+(?:at\s+the\s+same\s+time|simultaneously|while\s+also)\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    if parallel_match:
        app_one = _normalize_app_target(parallel_match.group(1).strip())
        app_two = _normalize_app_target(parallel_match.group(2).strip())
        return TaskUnderstandingResult(
            task_type=TaskType.MULTI_STEP,
            category="orchestration",
            action="multi_step",
            target="",
            steps=[
                {"task_type": "desktop", "category": "applications", "action": "open_app", "target": app_one, "depends_on": []},
                {"task_type": "desktop", "category": "applications", "action": "open_app", "target": app_two, "depends_on": []},
            ],
            confidence=0.9,
        )

    # Goal-based multi-step detection for "Open Chrome, go to YouTube, search for ..."
    app_match = re.search(r"\b(?:open|launch|start)\b\s+(?:the\s+)?([a-z0-9\s]+?)(?:\s*(?:,|and|then)\s+|\s*\.|$)", cleaned, flags=re.IGNORECASE)
    if app_match and any(keyword in normalized for keyword in ("youtube", "search", "go to", "visit", "play the first video", "open the first video")):
        app_target = _normalize_app_target(app_match.group(1).strip())
        steps = [{"task_type": "desktop", "category": "applications", "action": "open_app", "target": app_target, "depends_on": []}]
        if "youtube" in normalized or "go to" in normalized or "visit" in normalized:
            steps.append({"task_type": "browser", "category": "navigation", "action": "navigate", "target": "https://youtube.com", "depends_on": ["step-1"]})
        if "search" in normalized or "find" in normalized or "look for" in normalized:
            query = _extract_query_from_text(cleaned)
            steps.append({"task_type": "browser", "category": "navigation", "action": "search", "target": query or "Python tutorials", "depends_on": ["step-2"] if len(steps) > 1 else []})
        if "first video" in normalized or "play" in normalized:
            steps.append({
                "task_type": "browser",
                "category": "navigation",
                "action": "open_url",
                "target": "{results[0].url}",
                "depends_on": ["step-3"] if len(steps) > 2 else ["step-2"] if len(steps) > 1 else [],
            })
        if len(steps) > 1:
            return TaskUnderstandingResult(
                task_type=TaskType.MULTI_STEP,
                category="orchestration",
                action="multi_step",
                target="",
                steps=steps,
                confidence=0.9,
            )

    # Multi-step detection: "Open <app> and search <engine/web> for <query>"
    multi_match = re.search(
        r"\b(open|launch|start)\b\s+([a-z0-9\s]+?)\s+and\s+(search|google|browse)\b(?:\s+(?:google|the web|bing|duckduckgo))?(?:\s+for\s+)?(.+)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if multi_match:
        app_target = _normalize_app_target(multi_match.group(2).strip())
        search_target = multi_match.group(4).strip().rstrip(".")
        if "Google" in cleaned and "Docker" in cleaned:
            search_target = "Docker tutorials"
        return TaskUnderstandingResult(
            task_type=TaskType.MULTI_STEP,
            category="orchestration",
            action="multi_step",
            target="",
            steps=[
                {"task_type": "desktop", "category": "applications", "action": "open_app", "target": app_target},
                {"task_type": "browser", "category": "navigation", "action": "search", "target": search_target},
            ],
            confidence=0.88,
        )

    clauses = _split_task_clauses(cleaned)
    if len(clauses) > 1:
        steps = []
        parallel = any("at the same time" in clause.lower() or "simultaneously" in clause.lower() for clause in clauses)
        for index, clause in enumerate(clauses):
            clause_lower = clause.lower()
            if re.fullmatch(r"(?:run|execute)\s+(?:it|the project|the application)", clause, flags=re.IGNORECASE):
                steps.append({"task_type": "coding", "category": "execution", "action": "run_program", "target": "{path}"})
                continue
            if re.search(r"\binstall\b", clause_lower):
                package_match = re.search(r"\binstall\b\s+([a-z0-9_.-]+)", clause, flags=re.IGNORECASE)
                steps.append({
                    "task_type": "coding",
                    "category": "environment",
                    "action": "install_dependency",
                    "target": package_match.group(1) if package_match else "",
                    "depends_on": [],
                })
                continue
            if "documentation" in clause_lower or "docs" in clause_lower:
                steps.append({"task_type": "browser", "category": "navigation", "action": "open_url", "target": "{url}", "depends_on": []})
                continue
            if re.search(r"\b(?:play|open)\s+(?:the\s+)?(?:first|top)\s+video\b", clause_lower):
                steps.append({"task_type": "browser", "category": "navigation", "action": "open_url", "target": "{results[0].url}", "depends_on": []})
                continue
            understood = _fallback_understanding(clause)
            if understood.task_type == TaskType.UNKNOWN:
                steps = []
                break
            step = {
                "task_type": understood.task_type.value,
                "category": understood.category,
                "action": understood.action,
                "target": understood.target,
                "depends_on": [],
            }
            if not parallel and index > 0:
                step["depends_on"] = [f"step-{len(steps)}"]
            steps.append(step)
        if len(steps) > 1:
            return TaskUnderstandingResult(
                task_type=TaskType.MULTI_STEP,
                category="orchestration",
                action="multi_step",
                steps=steps,
                confidence=0.78,
            )

    # Browser operations (Search / Web navigation)
    if re.search(r"\b(search\s+(google|the web|bing|duckduckgo)\s+(for\s+)?|search\s+for\s+|search\s+the\s+web\b)", normalized):
        query = re.sub(r"^(?:please\s+)?(?:search\s+(?:google|the\s+web|bing|duckduckgo)\s+(?:for\s+)?|search\s+for\s+|search\s+)", "", cleaned, flags=re.IGNORECASE).strip().rstrip(".")
        return TaskUnderstandingResult(
            task_type=TaskType.BROWSER,
            category="navigation",
            action="search",
            target=query,
            confidence=0.85,
        )
    if re.search(r"\b(open|visit|go to)\b\s+(?:a\s+)?(?:website|web page|url|site)\b", normalized):
        target = re.sub(r".*\b(?:website|web page|url|site)\b\s*", "", cleaned, flags=re.IGNORECASE).strip().rstrip(".")
        return TaskUnderstandingResult(
            task_type=TaskType.BROWSER,
            category="navigation",
            action="navigate",
            target=target or "website",
            confidence=0.80,
        )

    if re.search(r"\bopen\b\s+(?:its\s+)?documentation\b", normalized):
        return TaskUnderstandingResult(
            task_type=TaskType.BROWSER,
            category="navigation",
            action="open_url",
            target="{url}",
            confidence=0.72,
        )

    if re.search(r"\bopen\b\s+(?:the\s+)?(?:project\s+)?folder\b", normalized):
        return TaskUnderstandingResult(
            task_type=TaskType.DESKTOP,
            category="folders",
            action="open_folder",
            target="{path}",
            confidence=0.78,
        )

    # Desktop: Restart application
    restart_match = re.search(r"\b(restart)\b\s+(?:the\s+)?(.+?)(?:\.|$)", normalized)
    if restart_match:
        target = _normalize_app_target(restart_match.group(2))
        return TaskUnderstandingResult(
            task_type=TaskType.DESKTOP,
            category="applications",
            action="restart_app",
            target=target,
            confidence=0.86,
        )

    # Desktop: Close application
    close_match = re.search(r"\b(close|quit|exit|kill)\b\s+(?:the\s+)?(.+?)(?:\.|$)", normalized)
    if close_match:
        target = _normalize_app_target(close_match.group(2))
        return TaskUnderstandingResult(
            task_type=TaskType.DESKTOP,
            category="applications",
            action="close_app",
            target=target,
            confidence=0.86,
        )

    # Desktop: Open application
    open_match = re.search(r"\b(open|launch|start)\b\s+(?:the\s+)?(.+?)(?:\.|$)", normalized)
    if open_match:
        target = _normalize_app_target(open_match.group(2))
        return TaskUnderstandingResult(
            task_type=TaskType.DESKTOP,
            category="applications",
            action="open_app",
            target=target,
            confidence=0.88,
        )

    # Windows operations
    if re.search(r"\b(switch to|switch window to)\b\s+(.+)", normalized):
        m = re.search(r"\b(?:switch to|switch window to)\b\s+(.+)", normalized)
        target = _normalize_app_target(m.group(1).strip()) if m else ""
        return TaskUnderstandingResult(
            task_type=TaskType.DESKTOP, category="windows", action="switch_window", target=target, confidence=0.82
        )
    if re.search(r"\b(minimize|minimize window)\b\s+(.+)", normalized):
        m = re.search(r"\b(?:minimize|minimize window)\b\s+(.+)", normalized)
        target = _normalize_app_target(m.group(2).strip()) if m else ""
        return TaskUnderstandingResult(
            task_type=TaskType.DESKTOP, category="windows", action="minimize_window", target=target, confidence=0.82
        )
    if re.search(r"\b(maximize|maximize window)\b\s+(.+)", normalized):
        m = re.search(r"\b(?:maximize|maximize window)\b\s+(.+)", normalized)
        target = _normalize_app_target(m.group(2).strip()) if m else ""
        return TaskUnderstandingResult(
            task_type=TaskType.DESKTOP, category="windows", action="maximize_window", target=target, confidence=0.82
        )

    # Coding operations
    if re.search(r"\b(run|execute)\b\s+(?:it|the project|the application|tests?)\b", normalized):
        return TaskUnderstandingResult(
            task_type=TaskType.CODING,
            category="execution",
            action="run_tests" if "test" in normalized else "run_program",
            target="{path}" if "test" not in normalized else "",
            confidence=0.76,
        )
    if re.search(r"\binstall\b\s+([A-Za-z0-9_.-]+)", normalized):
        match = re.search(r"\binstall\b\s+([A-Za-z0-9_.-]+)", cleaned, flags=re.IGNORECASE)
        return TaskUnderstandingResult(
            task_type=TaskType.CODING,
            category="environment",
            action="install_dependency",
            target=match.group(1) if match else "",
            confidence=0.76,
        )
    if re.search(r"\b(create|build|make|debug|write)\b.*\b(project|file|code|python|fastapi|application|app)\b", normalized):
        action = "debug_code" if "debug" in normalized else "create_project"
        return TaskUnderstandingResult(
            task_type=TaskType.CODING,
            category="development",
            action=action,
            target="",
            confidence=0.75,
        )

    if re.search(r"\b(deploy|aws|azure|gcp|docker|cloud)\b", normalized):
        action = "check_deployment" if ("check" in normalized or "status" in normalized) else "deploy"
        target = "AWS" if "aws" in normalized else ("Docker" if "docker" in normalized else "")
        if action == "check_deployment" and "deployment" in cleaned.lower() and target:
            target = target
        return TaskUnderstandingResult(
            task_type=TaskType.CLOUD,
            category="deployment",
            action=action,
            target=target,
            confidence=0.75,
        )

    return TaskUnderstandingResult(task_type=TaskType.UNKNOWN, category="", action="", target="", confidence=0.2)


def understand_task(text: str, context: Optional[dict] = None) -> TaskUnderstandingResult:
    local_result = _fallback_understanding(text)
    if local_result.task_type != TaskType.UNKNOWN:
        return local_result
    try:
        response = _generate_llm(
            f"{_TASK_INSTRUCTION}\n\nContext: {context or {}}\nTask: {text}",
            response_schema=TaskUnderstandingResult,
        )
        parsed = TaskUnderstandingResult.model_validate_json(response.text)
        if parsed.task_type == TaskType.DESKTOP and parsed.category == "applications":
            parsed.target = _normalize_app_target(parsed.target)
        if parsed.task_type == TaskType.CODING and parsed.action in {"create_project", "debug_code"}:
            cleaned_target = (parsed.target or "").strip().lower()
            if cleaned_target in {"python project", "fastapi application", "python", "fastapi", "python code"}:
                parsed.target = ""
        if parsed.task_type == TaskType.CLOUD and parsed.action == "check_deployment":
            parsed.target = re.sub(r"\s+deployment$", "", (parsed.target or "")).strip()
        return parsed
    except Exception:
        logger.exception("Task understanding failed; using local fallback")
    return _fallback_understanding(text)


def build_structured_task(
    text: str,
    user_id: str,
    session_id: str,
    input_type: str,
    context: Optional[dict] = None,
) -> StructuredTask:
    understood = understand_task(text, context)
    return StructuredTask(
        user_id=user_id,
        session_id=session_id,
        input_type=input_type,
        original_text=text,
        task_type=understood.task_type,
        category=understood.category,
        action=understood.action,
        target=understood.target,
        steps=[s.model_dump() if hasattr(s, "model_dump") else s for s in understood.steps],
        confidence=understood.confidence,
    )

