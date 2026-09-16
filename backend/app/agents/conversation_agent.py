import logging
from typing import Any, Dict, List, Optional

from app.core.classify import _generate_llm

logger = logging.getLogger(__name__)

CONVERSATION_SYSTEM_INSTRUCTION = """
You are EVI, a friendly personal desktop AI assistant.
For casual conversation, respond naturally and conversationally.
Keep simple conversations concise, warm, and human-like.
Use the recent conversation history to understand context and continue the discussion.
Do not describe internal reasoning, tools, agents, APIs, or system architecture unless
the user specifically asks. Do not execute desktop actions for casual conversation.
If the user is actually asking for a task, let the intent/task pipeline handle it.
Return only the final user-facing response text, with no labels or analysis.
""".strip()


def _fallback_response() -> str:
    return "I'm here with you and ready to chat. What are you working on?"


def generate_conversation_response(
    transcript: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    working_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a natural casual response using EVI's configured Gemini client."""
    prompt = (
        f"{CONVERSATION_SYSTEM_INSTRUCTION}\n\n"
        f"Working context:\n{working_context or {}}\n\n"
        f"Recent conversation history:\n{conversation_history or []}\n\n"
        f"User transcript:\n{transcript}"
    )
    try:
        response = _generate_llm(prompt, temperature=0.7)
        final_text = (response.text or "").strip()
        return final_text or _fallback_response()
    except Exception:
        logger.exception("Conversation agent failed to generate a response")
        return _fallback_response()