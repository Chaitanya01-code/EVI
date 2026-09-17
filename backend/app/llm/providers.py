from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Optional, Type

from app.llm.config import OPENROUTER_BASE_URL, PRIMARY_MODEL, ModelConfig
from app.llm.models import ProviderFailure


class LLMProvider:
    name = "unknown"

    async def generate(self, prompt: str, model: str, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> str:
        raise NotImplementedError

    def generate_sync(self, prompt: str, model: str, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> str:
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    name = "gemini"

    async def generate(self, prompt: str, model: str = PRIMARY_MODEL, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> str:
        from app.core.classify import _get_client

        client = _get_client()
        if client is None:
            raise RuntimeError("Gemini API key or client is unavailable")
        config = {"temperature": temperature}
        if response_schema is not None:
            config.update({"response_mime_type": "application/json", "response_schema": response_schema})
        aio_client = getattr(client, "aio", None)
        if aio_client is not None:
            response = await aio_client.models.generate_content(model=model, contents=prompt, config=config)
        else:
            response = await asyncio.to_thread(client.models.generate_content, model=model, contents=prompt, config=config)
        text = getattr(response, "text", "") or ""
        if not text.strip():
            raise RuntimeError("Gemini returned an empty response")
        return text.strip()

    def generate_sync(self, prompt: str, model: str = PRIMARY_MODEL, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> str:
        from app.core.classify import _get_client

        client = _get_client()
        if client is None:
            raise RuntimeError("Gemini API key or client is unavailable")
        config = {"temperature": temperature}
        if response_schema is not None:
            config.update({"response_mime_type": "application/json", "response_schema": response_schema})
        response = client.models.generate_content(model=model, contents=prompt, config=config)
        text = getattr(response, "text", "") or ""
        if not text.strip():
            raise RuntimeError("Gemini returned an empty response")
        return text.strip()


class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    async def generate(self, prompt: str, model: str, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> str:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OpenRouter API key is unavailable")
        try:
            import httpx
        except ImportError as error:
            raise RuntimeError("httpx is required for OpenRouter fallback") from error
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:8000"),
                    "X-Title": "EVI",
                },
                json=payload,
            )
            if response.status_code >= 400:
                retry_after = response.headers.get("Retry-After")
                try:
                    retry_after_value = float(retry_after) if retry_after else None
                except ValueError:
                    retry_after_value = None
                raise ProviderFailure(
                    f"OpenRouter request failed with HTTP {response.status_code}",
                    status_code=response.status_code,
                    retry_after=retry_after_value,
                )
            data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("OpenRouter returned an empty response")
        return text.strip()

    def generate_sync(self, prompt: str, model: str, response_schema: Optional[Type[Any]] = None, temperature: float = 0) -> str:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OpenRouter API key is unavailable")
        try:
            import httpx
        except ImportError as error:
            raise RuntimeError("httpx is required for OpenRouter fallback") from error
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
        with httpx.Client(timeout=None) as client:
            response = client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:8000"),
                    "X-Title": "EVI",
                },
                json=payload,
            )
            if response.status_code >= 400:
                retry_after = response.headers.get("Retry-After")
                try:
                    retry_after_value = float(retry_after) if retry_after else None
                except ValueError:
                    retry_after_value = None
                raise ProviderFailure(
                    f"OpenRouter request failed with HTTP {response.status_code}",
                    status_code=response.status_code,
                    retry_after=retry_after_value,
                )
            data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("OpenRouter returned an empty response")
        return text.strip()


PROVIDERS = {"gemini": GeminiProvider(), "openrouter": OpenRouterProvider()}
