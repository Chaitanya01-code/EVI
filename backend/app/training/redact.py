from __future__ import annotations

import re


_KEY_VALUE_RE = re.compile(
    r"""(?i)\b([A-Za-z0-9_.-]*(?:password|secret|token|key)[A-Za-z0-9_.-]*)\s*=\s*"""
    r"""(?:"[^"]*"|'[^']*'|[^\s,;&]+)"""
)
_API_TOKEN_PATTERNS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]+\b"), "[REDACTED_KEY]"),
    (re.compile(r"\bAIza[A-Za-z0-9_-]+\b"), "[REDACTED_KEY]"),
    (re.compile(r"\bghp_[A-Za-z0-9]+\b"), "[REDACTED_KEY]"),
    (re.compile(r"\bBearer\s+\S+", re.IGNORECASE), "[REDACTED_TOKEN]"),
)
_LONG_TOKEN_PATTERNS = (
    (re.compile(r"(?<![A-Za-z0-9])[A-Fa-f0-9]{24,}(?![A-Za-z0-9])"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9+/_=-]{24,}(?![A-Za-z0-9])"), "[REDACTED_TOKEN]"),
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\w)\+?[\d().\-\s]{9,}\d(?!\w)")


def _redact_phone(match: re.Match[str]) -> str:
    digits = sum(character.isdigit() for character in match.group())
    return "[REDACTED_PHONE]" if 10 <= digits <= 15 else match.group()


def redact(text: str) -> str:
    """Mask common credentials and personal contact details in text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    redacted = _KEY_VALUE_RE.sub(lambda match: f"{match.group(1)}=[REDACTED_KEY]", text)
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    for pattern, placeholder in _API_TOKEN_PATTERNS:
        redacted = pattern.sub(placeholder, redacted)
    redacted = _PHONE_RE.sub(_redact_phone, redacted)
    for pattern, placeholder in _LONG_TOKEN_PATTERNS:
        redacted = pattern.sub(placeholder, redacted)
    return redacted
