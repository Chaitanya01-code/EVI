from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type

from app.llm.config import FALLBACK_MODELS, MODEL_TIMEOUT_SECONDS, PRIMARY_MODEL, ModelConfig
from app.llm.models import LLMFailure, LLMResponse, ModelStatus, ProviderFailure
from app.llm.providers import PROVIDERS

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self, timeout_seconds: Optional[float] = None) -> None:
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else MODEL_TIMEOUT_SECONDS
        self.last_response: Optional[LLMResponse] = None
        self.statuses = {
            PRIMARY_MODEL: ModelStatus("Gemini", "gemini", PRIMARY_MODEL),
            **{config.model: ModelStatus(config.name, config.provider, config.model) for config in FALLBACK_MODELS},
        }

    def models(self) -> list[ModelConfig]:
        return [ModelConfig("Gemini", "gemini", PRIMARY_MODEL), *FALLBACK_MODELS]

    async def generate(self, prompt: str, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> LLMResponse:
        attempts = []
        logger.info("LLM request started")
        for attempt, config in enumerate(self.models(), 1):
            if config.provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
                logger.warning("LLM provider unavailable provider=openrouter reason=missing_api_key")
                break
            provider = PROVIDERS.get(config.model) or PROVIDERS.get(config.provider)
            if provider is None:
                error = f"provider implementation unavailable for {config.provider}"
                logger.warning("LLM attempt failed provider=%s model=%s attempt=%s error=%s", config.provider, config.model, attempt, error)
                attempts.append({"provider": config.provider, "model": config.model, "attempt": attempt, "error": error})
                continue
            started = time.perf_counter()
            logger.info("LLM provider selected provider=%s model=%s attempt=%s", config.provider, config.model, attempt)
            logger.info("LLM provider request started provider=%s model=%s", config.provider, config.model)
            request = asyncio.create_task(provider.generate(prompt, config.model, response_schema, temperature))
            try:
                text = await asyncio.wait_for(request, timeout=self.timeout_seconds)
                latency = round((time.perf_counter() - started) * 1000, 2)
                response = LLMResponse(text, config.provider, config.model, attempt, latency, attempt > 1)
                self.last_response = response
                status = self.statuses[config.model]
                status.available = True
                status.last_success = datetime.now(timezone.utc).isoformat()
                status.last_latency_ms = latency
                logger.info("LLM response received provider=%s model=%s latency_ms=%s", config.provider, config.model, latency)
                return response
            except asyncio.TimeoutError:
                request.cancel()
                await asyncio.gather(request, return_exceptions=True)
                logger.warning("LLM timeout provider=%s model=%s attempt=%s timeout=%ss", config.provider, config.model, attempt, self.timeout_seconds)
                error = f"timeout after {self.timeout_seconds}s"
            except asyncio.CancelledError:
                request.cancel()
                await asyncio.gather(request, return_exceptions=True)
                raise
            except Exception as exc:
                error = str(exc)
                status_code = getattr(exc, "status_code", None)
                if status_code == 402:
                    failure_class = "payment_required"
                elif status_code == 429:
                    failure_class = "rate_limited"
                else:
                    failure_class = "provider_error"
                logger.warning("LLM provider failure classified provider=%s model=%s class=%s status=%s", config.provider, config.model, failure_class, status_code)
                if status_code == 429 and getattr(exc, "retry_after", None) is not None and attempt < len(self.models()):
                    delay = min(max(float(exc.retry_after), 0.0), 2.0)
                    if delay:
                        await asyncio.sleep(delay)
                logger.warning("LLM attempt failed provider=%s model=%s attempt=%s error=%s", config.provider, config.model, attempt, error)
            status = self.statuses[config.model]
            status.available = False
            status.failure_count += 1
            status.last_failure = datetime.now(timezone.utc).isoformat()
            attempts.append({"provider": config.provider, "model": config.model, "attempt": attempt, "error": error})
            if attempt < len(self.models()):
                next_model = self.models()[attempt]
                logger.info("LLM fallback from=%s to=%s model=%s attempt=%s", config.provider, next_model.provider, next_model.model, attempt + 1)
        logger.error("LLM request completed success=false provider_count=%s", len(attempts))
        raise LLMFailure("All configured LLM providers are unavailable.", attempts)

    def generate_sync(self, prompt: str, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> LLMResponse:
        attempts = []
        logger.info("LLM request started mode=sync")
        for attempt, config in enumerate(self.models(), 1):
            if config.provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
                logger.warning("LLM provider unavailable provider=openrouter reason=missing_api_key")
                break
            provider = PROVIDERS.get(config.model) or PROVIDERS.get(config.provider)
            if provider is None or not hasattr(provider, "generate_sync"):
                attempts.append({"provider": config.provider, "model": config.model, "attempt": attempt, "error": "sync provider unavailable"})
                continue
            started = time.perf_counter()
            logger.info("LLM provider selected provider=%s model=%s attempt=%s mode=sync", config.provider, config.model, attempt)
            try:
                text = provider.generate_sync(prompt, config.model, response_schema, temperature)
                latency = round((time.perf_counter() - started) * 1000, 2)
                response = LLMResponse(text, config.provider, config.model, attempt, latency, attempt > 1)
                self.last_response = response
                status = self.statuses[config.model]
                status.available = True
                status.last_success = datetime.now(timezone.utc).isoformat()
                status.last_latency_ms = latency
                logger.info("LLM response received provider=%s model=%s latency_ms=%s mode=sync", config.provider, config.model, latency)
                return response
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                failure_class = "payment_required" if status_code == 402 else "rate_limited" if status_code == 429 else "provider_error"
                logger.warning("LLM provider failure classified provider=%s model=%s class=%s status=%s mode=sync", config.provider, config.model, failure_class, status_code)
                status = self.statuses[config.model]
                status.available = False
                status.failure_count += 1
                status.last_failure = datetime.now(timezone.utc).isoformat()
                attempts.append({"provider": config.provider, "model": config.model, "attempt": attempt, "error": str(exc), "class": failure_class})
        logger.error("LLM request completed success=false provider_count=%s mode=sync", len(attempts))
        raise LLMFailure("All configured LLM providers are unavailable.", attempts)


llm_router = LLMRouter()
