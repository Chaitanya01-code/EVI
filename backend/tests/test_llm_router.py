import asyncio
import unittest
from unittest.mock import patch

from app.llm.config import FALLBACK_MODELS
from app.llm.models import LLMFailure
from app.llm.router import LLMRouter


class FakeProvider:
    def __init__(self, result=None, error=None, wait=False):
        self.result = result
        self.error = error
        self.wait = wait
        self.cancelled = False

    async def generate(self, *args, **kwargs):
        try:
            if self.wait:
                await asyncio.sleep(10)
            if self.error:
                raise self.error
            return self.result
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class LLMRouterTests(unittest.IsolatedAsyncioTestCase):
    def _providers(self, sequence):
        return {"gemini": sequence[0], **{config.model: provider for config, provider in zip(FALLBACK_MODELS, sequence[1:])}}

    async def test_gemini_success_stops_chain(self):
        providers = self._providers([FakeProvider("primary"), *[FakeProvider("unused") for _ in FALLBACK_MODELS]])
        with patch("app.llm.router.PROVIDERS", providers), patch("app.llm.router.os.getenv", return_value="key"):
            response = await LLMRouter(timeout_seconds=0.05).generate("hello")
        self.assertEqual(response.text, "primary")
        self.assertEqual(response.attempt, 1)
        self.assertFalse(response.fallback_used)

    async def test_timeout_cancels_gemini_and_uses_first_fallback(self):
        first = FakeProvider(wait=True)
        providers = self._providers([first, FakeProvider("fallback"), *[FakeProvider("unused") for _ in FALLBACK_MODELS[1:]]])
        with patch("app.llm.router.PROVIDERS", providers), patch("app.llm.router.os.getenv", return_value="key"):
            response = await LLMRouter(timeout_seconds=0.01).generate("hello")
        self.assertTrue(first.cancelled)
        self.assertEqual(response.model, FALLBACK_MODELS[0].model)
        self.assertTrue(response.fallback_used)

    async def test_chain_stops_after_second_fallback_success(self):
        sequence = [FakeProvider(wait=True), FakeProvider(wait=True), FakeProvider("second fallback"), *[FakeProvider("unused") for _ in FALLBACK_MODELS[2:]]]
        providers = self._providers(sequence)
        with patch("app.llm.router.PROVIDERS", providers), patch("app.llm.router.os.getenv", return_value="key"):
            response = await LLMRouter(timeout_seconds=0.01).generate("hello")
        self.assertEqual(response.attempt, 3)

    async def test_all_fail_returns_controlled_failure(self):
        providers = self._providers([FakeProvider(error=RuntimeError("down")) for _ in range(1 + len(FALLBACK_MODELS))])
        with patch("app.llm.router.PROVIDERS", providers), patch("app.llm.router.os.getenv", return_value="key"):
            with self.assertRaises(LLMFailure) as failure:
                await LLMRouter(timeout_seconds=0.01).generate("hello")
        self.assertEqual(len(failure.exception.attempts), 6)


if __name__ == "__main__":
    unittest.main()
