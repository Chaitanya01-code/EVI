from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConversationRecord(BaseModel):
    session_id: str
    user_id: str
    user_message: str
    input_type: str
    response_type: str
    intent: str
    mode: str
    action: str
    target: str
    confidence: float
    status: str
    evi_response: str
    timestamp: datetime

    def as_db_values(self) -> tuple[Any, ...]:
        return (
            self.session_id,
            self.user_id,
            self.user_message,
            self.input_type,
            self.response_type,
            self.intent,
            self.mode,
            self.action,
            self.target,
            self.confidence,
            self.status,
            self.evi_response,
            self.timestamp.isoformat(),
        )
