from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.core.classify import GEMINI_MODEL, _get_client
from app.task.task_models import StructuredTask, TaskType

logger = logging.getLogger(__name__)


class TaskUnderstandingResult(BaseModel):
    task_type: TaskType
    action: str
    target: str = ""
    confidence: float = Field(ge=0, le=1)


_TASK_INSTRUCTION = """
You are EVI's task understanding layer. Convert an executable user request into JSON.
Choose exactly one task_type: desktop, coding, cloud, browser, unknown.
Examples: opening VS Code is desktop/open_application/Visual Studio Code;
creating a Python project is coding/create_project; searching Google is
browser/search_web; deploying to AWS is cloud/deploy. Do not execute anything.
Return only task_type, action, target, confidence.
""".strip()


def _fallback_understanding(text: str) -> TaskUnderstandingResult:
    normalized = text.lower().strip()
    patterns = (
        (r"\b(vs code|visual studio code)\b", TaskType.DESKTOP, "open_application", "Visual Studio Code", 0.9),
        (r"\b(create|build|make)\b.*\b(project|file|code|python|fastapi)\b", TaskType.CODING, "create_project", "", 0.72),
        (r"\b(search|google|browse)\b", TaskType.BROWSER, "search_web", "", 0.7),
        (r"\b(deploy|aws|azure|gcp|cloud)\b", TaskType.CLOUD, "deploy", "", 0.7),
    )
    for pattern, task_type, action, target, confidence in patterns:
        if re.search(pattern, normalized):
            return TaskUnderstandingResult(
                task_type=task_type, action=action, target=target, confidence=confidence
            )
    return TaskUnderstandingResult(task_type=TaskType.UNKNOWN, action="", confidence=0.2)


def understand_task(text: str, context: Optional[dict] = None) -> TaskUnderstandingResult:
    client = _get_client()
    if client is not None:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"{_TASK_INSTRUCTION}\n\nContext: {context or {}}\nTask: {text}",
                config={
                    "response_mime_type": "application/json",
                    "response_schema": TaskUnderstandingResult,
                    "temperature": 0,
                },
            )
            return TaskUnderstandingResult.model_validate_json(response.text)
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
        action=understood.action,
        target=understood.target,
        confidence=understood.confidence,
    )
