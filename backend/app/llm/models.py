from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    attempt: int
    latency_ms: float
    fallback_used: bool
    success: bool = True


@dataclass
class ModelStatus:
    name: str
    provider: str
    model: str
    enabled: bool = True
    available: bool = True
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    last_latency_ms: Optional[float] = None
    failure_count: int = 0


@dataclass
class LLMFailure(Exception):
    message: str
    attempts: list[Dict[str, Any]] = field(default_factory=list)

    def __str__(self) -> str:
        return self.message


class ProviderFailure(RuntimeError):
    """A provider error with safe HTTP metadata for retry decisions."""

    def __init__(self, message: str, status_code: int | None = None, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
