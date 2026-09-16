from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.agents.conversation_agent import generate_conversation_response
from app.core.classify import IntentResult, classify_input, generate_response
from app.core.context import WorkingContext
from app.database.models import ConversationRecord, TaskRecord
from app.database.store import save_or_update_task_record_async, save_record_async
from app.memory.memory_service import process_memory_async, retrieve_user_memories
from app.task.task_manager import TaskManager
from app.task.task_models import TaskExecutionResult, TaskStatus
from app.task.task_router import TaskRouter, build_default_registry
from app.task.task_understanding import build_structured_task
from app.router.schemas import ProcessingResponse
from app.voice.text_to_speech import synthesize_audio_async

logger = logging.getLogger(__name__)
_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
_task_manager = TaskManager(TaskRouter(build_default_registry()))


async def _route_response(context: WorkingContext, classification: IntentResult):
    if classification.mode == "conversation":
        return generate_conversation_response(
            transcript=context.transcript,
            conversation_history=context.conversation_history,
            working_context=context.as_prompt_context(),
        ), None
    if classification.mode == "unclear":
        return "I wasn't sure what you meant. Could you rephrase that or tell me what you want me to do?", None
    if classification.mode == "task":
        loop = asyncio.get_running_loop()
        task = await loop.run_in_executor(
            None,
            build_structured_task,
            context.transcript,
            context.user_id,
            context.session_id,
            context.input_type,
            context.as_prompt_context(),
        )

        initial_record = TaskRecord(
            task_id=task.task_id,
            session_id=task.session_id,
            user_id=task.user_id,
            task_type=task.task_type.value,
            agent_type="pending",
            category=task.category,
            action=task.action,
            target=task.target,
            status=TaskStatus.PENDING.value,
            success=False,
            verified=False,
            message="Task initialized",
            timestamp=datetime.now(timezone.utc),
        )
        asyncio.create_task(save_or_update_task_record_async(initial_record))

        result: TaskExecutionResult = await loop.run_in_executor(
            None, _task_manager.execute, task
        )

        final_record = TaskRecord(
            task_id=task.task_id,
            session_id=task.session_id,
            user_id=task.user_id,
            task_type=task.task_type.value,
            agent_type=result.agent,
            category=task.category,
            action=task.action,
            target=task.target,
            status=result.status.value,
            success=result.success,
            verified=result.verified,
            message=result.message,
            timestamp=datetime.now(timezone.utc),
        )
        asyncio.create_task(save_or_update_task_record_async(final_record))

        return result.message, result
    return generate_response(context.transcript, classification, context.as_prompt_context()), None


async def process_context(context: WorkingContext) -> ProcessingResponse:
    loop = asyncio.get_running_loop()
    context.memories = await loop.run_in_executor(
        None, retrieve_user_memories, context.user_id
    )
    classification = await loop.run_in_executor(
        None, classify_input, context.transcript, context.as_prompt_context()
    )
    response, task_result = await _route_response(context, classification)
    response_type = "voice" if context.input_type == "voice" else "text"
    audio = ""
    tts_error = None
    if response_type == "voice":
        try:
            audio = await synthesize_audio_async(response)
            if not audio:
                tts_error = "Voice response is unavailable, but the text response is ready."
        except Exception:
            tts_error = "Voice response is unavailable, but the text response is ready."
    status = "clarification" if classification.mode == "unclear" else "completed"
    if task_result is not None and not task_result.success:
        status = "fallback"
    record = ConversationRecord(
        session_id=context.session_id,
        user_id=context.user_id,
        user_message=context.transcript,
        input_type=context.input_type,
        response_type=response_type,
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
    asyncio.create_task(process_memory_async(
        context.user_id,
        context.transcript,
        context.as_prompt_context(),
    ))
    return ProcessingResponse(
        session_id=context.session_id,
        transcript=context.transcript,
        input_type=context.input_type,
        classification=classification,
        status=status,
        response=response,
        response_type=response_type,
        text=response,
        audio=audio,
        tts_error=tts_error,
        task_result=task_result,
        timestamp=context.timestamp,
    )


def conversation_history(session_id: str) -> list[dict[str, Any]]:
    return _history[session_id][-10:]
