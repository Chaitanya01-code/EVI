from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.core.classify import IntentResult
from app.task.task_models import TaskExecutionResult


class ChatRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = None
    input_type: Literal["voice", "text"] = "text"
    user_id: str = Field(default="default-user", min_length=1, max_length=200)


class ProcessingResponse(BaseModel):
    session_id: str
    transcript: str
    input_type: Literal["voice", "text"]
    classification: IntentResult
    status: Literal["completed", "fallback", "clarification"]
    response: str
    response_type: Literal["text", "voice"]
    text: str
    audio: str = ""
    tts_error: Optional[str] = None
    task_result: Optional[TaskExecutionResult] = None
    timestamp: datetime
