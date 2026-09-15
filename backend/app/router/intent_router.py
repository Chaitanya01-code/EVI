from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.core.classify import IntentResult, classify_input, generate_response
from app.core.context import WorkingContext
from app.database.models import ConversationRecord
from app.database.store import save_record_async
from app.router.schemas import ProcessingResponse
from app.voice.text_to_speech import speak_text_async

logger = logging.getLogger(__name__)
_history: dict[str, list[dict[str, Any]]] = defaultdict(list)


def _route_response(context: WorkingContext, classification: IntentResult) -> str:
    if classification.mode == "unclear":
        return "I wasn't sure what you meant. Could you rephrase that or tell me what you want me to do?"
    if classification.mode == "task":
        return (
            f"I can plan that task: {classification.action or classification.intent}"
            f" for {classification.target or 'the requested target'}."
        )
    return generate_response(context.transcript, classification, context.as_prompt_context())


async def process_context(context: WorkingContext) -> ProcessingResponse:
    loop = asyncio.get_running_loop()
    classification = await loop.run_in_executor(
        None, classify_input, context.transcript, context.as_prompt_context()
    )
    response = _route_response(context, classification)
    status = "clarification" if classification.mode == "unclear" else "completed"
    record = ConversationRecord(
        session_id=context.session_id,
        user_message=context.transcript,
        input_type=context.input_type,
        intent=classification.intent,
        mode=classification.mode,
        action=classification.action,
        target=classification.target,
        confidence=classification.confidence,
        status=status,
        evi_response=response,
        timestamp=context.timestamp,
    )
    _history[context.session_id].append({
        "user_message": context.transcript,
        "mode": classification.mode,
        "response": response,
        "timestamp": context.timestamp.isoformat(),
    })
    asyncio.create_task(save_record_async(record))
    asyncio.create_task(speak_text_async(response))
    return ProcessingResponse(
        session_id=context.session_id,
        transcript=context.transcript,
        input_type=context.input_type,
        classification=classification,
        status=status,
        response=response,
        timestamp=context.timestamp,
    )


def conversation_history(session_id: str) -> list[dict[str, Any]]:
    return _history[session_id][-10:]
