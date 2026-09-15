import os
import logging
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()
logger = logging.getLogger(__name__)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


# --------------------------------------------------
# Structured result returned by Gemini
# --------------------------------------------------

class IntentResult(BaseModel):
    mode: Literal[
        "conversation",
        "task",
        "question",
        "unclear"
    ] = Field(
        description="The main type of user request."
    )

    intent: str = Field(
        description="Specific intent, such as casual_chat, open_application, "
                    "search_web, read_file, create_file, or coding_help."
    )

    action: str = Field(
        description="The executable action, or an empty string when none is needed."
    )

    confidence: float = Field(ge=0, le=1, description="Confidence between 0 and 1.")

    requires_action: bool = Field(
        description="True when EVI needs to perform an external action."
    )

    target: str = Field(
        description="The application, file, website, or object involved. "
                    "Use an empty string if there is no target."
    )

    reason: str = Field(
        description="Short explanation of why the request was classified this way."
    )


# --------------------------------------------------
# Gemini client
# --------------------------------------------------

_client = None


def _get_client():
    global _client
    if _client is None and os.getenv("GEMINI_API_KEY"):
        try:
            from google import genai

            _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        except Exception:
            logger.exception("Unable to initialize Gemini client")
    return _client


# --------------------------------------------------
# Classifier
# --------------------------------------------------

def _fallback_classification(user_input: str) -> IntentResult:
    text = user_input.strip().lower()
    if not text:
        return IntentResult(
            mode="unclear", intent="missing_input", action="", target="",
            confidence=1, requires_action=False, reason="No transcript was provided."
        )
    if any(greeting in text for greeting in (
        "hey evi", "hello", "hi evi", "how are you", "good morning",
        "thank you", "thanks", "that's interesting", "im working", "i'm working",
    )):
        return IntentResult(
            mode="conversation", intent="casual_chat", action="", target="",
            confidence=0.86, requires_action=False, reason="The user is making conversation."
        )
    if text.startswith(("what ", "why ", "how ", "who ", "when ", "where ")) or text.endswith("?"):
        return IntentResult(
            mode="question", intent="general_question", action="", target="",
            confidence=0.8, requires_action=False, reason="The user is asking for information."
        )
    if "search" in text and ("chrome" in text or "youtube" in text):
        return IntentResult(
            mode="task", intent="browser_search", action="open_and_search", target="YouTube",
            confidence=0.76, requires_action=True, reason="The user requested a browser search."
        )
    if text.startswith(("open ", "launch ", "start ")):
        target = text.split(maxsplit=1)[1].strip()
        return IntentResult(
            mode="task", intent="open_application", action="open_application", target=target,
            confidence=0.78, requires_action=True, reason="The user asked EVI to open something."
        )
    if any(term in text for term in ("create a python", "create a project", "deploy", "search google")):
        return IntentResult(
            mode="task", intent="execute_task", action="", target="",
            confidence=0.7, requires_action=True, reason="The user requested an executable task."
        )
    return IntentResult(
        mode="unclear", intent="unclear_request", action="", target="",
        confidence=0.45, requires_action=False,
        reason="The request does not identify a reliable intent."
    )


def classify_input(user_input: str, context: Optional[dict] = None) -> IntentResult:

    prompt = f"""
You are EVI's intent classification system.

Your job is NOT to answer the user.

Your job is to determine what the user wants.

Classify the input into exactly one of:

1. conversation
   - Casual conversation
   - Greetings
   - Jokes
   - Personal discussion
   - General chatting

2. task
   - User wants EVI to perform an action
   - Opening applications
   - Closing applications
   - Creating files
   - Reading files
   - Searching the web
   - Controlling the desktop
   - Running commands
   - Coding actions
   - Browser actions
   - Other executable actions

3. question
   - User wants information or an explanation
   - No external action is necessarily required

4. unclear
   - Intent cannot be determined reliably

IMPORTANT:
- Do NOT classify based only on individual keywords.
- Understand the complete meaning.
- "How do I open Chrome?" is a question.
- "Open Chrome" is a task.
- "Why does Chrome open automatically?" is a question.
- "Hey EVI, how are you?" is conversation.
- "Open VS Code and run my project." is a task.
- If the user asks EVI to actually DO something, use task.
- If the user only asks HOW or WHY, use question.

Return JSON with exactly these fields: mode, intent, action, target, confidence,
requires_action, and reason. The action must be empty for conversation, question,
and unclear requests.

User input:

{user_input}
"""

    client = _get_client()
    if client is None:
        logger.warning("Gemini unavailable; using local classification fallback")
        return _fallback_classification(user_input)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"Conversation context:\n{context or {}}\n\n{prompt}",
            config={
                "response_mime_type": "application/json",
                "response_schema": IntentResult,
                "temperature": 0,
            },
        )
        return IntentResult.model_validate_json(response.text)
    except Exception:
        logger.exception("Gemini classification failed; using local fallback")
        return _fallback_classification(user_input)


def generate_response(user_input: str, result: IntentResult, context: Optional[dict] = None) -> str:
    """Generate an agent response using the shared Gemini client, with a safe fallback."""
    client = _get_client()
    if client is not None:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=(
                    "You are EVI, a concise desktop assistant. Respond naturally to the user. "
                    f"Classification: {result.model_dump_json()}\nContext: {context or {}}\n"
                    f"User: {user_input}"
                ),
            )
            if response.text:
                return response.text.strip()
        except Exception:
            logger.exception("Gemini response generation failed")
    if result.mode == "conversation":
        return "I'm doing well and ready to help."
    if result.mode == "question":
        return "I can help answer that, but my reasoning service is temporarily unavailable."
    if result.mode == "task":
        return f"I understood that you want me to {result.action or 'perform a task'} for {result.target or 'your request'}."
    return "I wasn't sure what you meant. Could you rephrase that?"


# --------------------------------------------------
# Test
# --------------------------------------------------

if __name__ == "__main__":

    while True:

        user_input = input("\nYou: ")

        if user_input.lower() in {"exit", "quit"}:
            break

        result = classify_input(user_input)

        print("\nEVI CLASSIFICATION")
        print("------------------")
        print(f"Mode:             {result.mode}")
        print(f"Intent:           {result.intent}")
        print(f"Confidence:       {result.confidence}")
        print(f"Requires action:  {result.requires_action}")
        print(f"Target:           {result.target}")
        print(f"Reason:           {result.reason}")