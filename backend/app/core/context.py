from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkingContext(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = "default-user"
    transcript: str = Field(min_length=1)
    input_type: Literal["voice", "text"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    memories: List[Dict[str, Any]] = Field(default_factory=list)

    def as_prompt_context(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "input_type": self.input_type,
            "timestamp": self.timestamp.isoformat(),
            "conversation_history": self.conversation_history[-10:],
            "memories": self.memories,
        }
