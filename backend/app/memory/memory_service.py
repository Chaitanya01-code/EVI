from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.classify import _generate_llm
from app.database.store import delete_memory, retrieve_memories, upsert_memory
from app.memory.schemas import MemoryExtraction

logger = logging.getLogger(__name__)
_BLOCKED_MEMORY_TERMS = ("api_key", "apikey", "password", "secret", "token", "credential")

_MEMORY_INSTRUCTION = """
You extract only durable, user-specific facts worth remembering across sessions.
Do not store greetings, opinions about the current conversation, transient tasks,
questions, secrets, API keys, passwords, or sensitive credentials.
Support profile facts such as a preferred name. For 'forget my name', return delete
with key preferred_name. For a changed name such as 'call me Alex', return upsert.
Return JSON only with remember, operation, key, value, memory_type, confidence.
If there is nothing durable to remember, return remember=false and operation=none.
""".strip()


def extract_memory(transcript: str, context: Optional[Dict[str, Any]] = None) -> MemoryExtraction:
    try:
        result = _generate_llm(
            f"{_MEMORY_INSTRUCTION}\n\nContext: {context or {}}\nUser: {transcript}",
            response_schema=MemoryExtraction,
        )
        return MemoryExtraction.model_validate_json(result.text)
    except Exception:
        logger.exception("Memory extraction failed")
        return MemoryExtraction()


def apply_memory(user_id: str, extraction: MemoryExtraction) -> None:
    if not extraction.remember or not extraction.key:
        return
    normalized_key = extraction.key.strip().lower()
    if any(term in normalized_key for term in _BLOCKED_MEMORY_TERMS):
        logger.warning("Rejected credential-like memory key")
        return
    if extraction.operation == "delete":
        delete_memory(user_id, extraction.key)
    elif extraction.operation == "upsert" and extraction.value:
        upsert_memory(
            user_id,
            extraction.key,
            extraction.value,
            extraction.memory_type,
            extraction.confidence,
        )


def retrieve_user_memories(user_id: str) -> List[Dict[str, Any]]:
    try:
        return retrieve_memories(user_id)
    except Exception:
        logger.exception("Memory retrieval failed")
        return []


async def process_memory_async(user_id: str, transcript: str, context: Dict[str, Any]) -> None:
    loop = asyncio.get_running_loop()
    extraction = await loop.run_in_executor(None, extract_memory, transcript, context)
    try:
        await loop.run_in_executor(None, apply_memory, user_id, extraction)
    except Exception:
        logger.exception("Memory update failed")
