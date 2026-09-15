import unittest
from unittest.mock import AsyncMock, patch

from app.core.classify import classify_input
from app.core.context import WorkingContext
from app.router.intent_router import process_context


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.gemini = patch("app.core.classify._get_client", return_value=None)
        self.gemini.start()
        self.persistence = patch("app.router.intent_router.save_record_async", new_callable=AsyncMock)
        self.persistence.start()

    async def asyncTearDown(self):
        self.persistence.stop()
        self.gemini.stop()

    async def test_conversation(self):
        result = classify_input("Hey EVI, how are you?")
        self.assertEqual(result.mode, "conversation")

    async def test_question(self):
        result = classify_input("What is machine learning?")
        self.assertEqual(result.mode, "question")

    async def test_task(self):
        result = classify_input("Open VS Code")
        self.assertEqual(result.mode, "task")
        self.assertEqual(result.action, "open_application")

    async def test_unclear(self):
        result = classify_input("I don't know what to do")
        self.assertEqual(result.mode, "unclear")

    async def test_pipeline_returns_routed_response(self):
        result = await process_context(WorkingContext(
            transcript="Open VS Code",
            input_type="text",
        ))
        self.assertEqual(result.classification.mode, "task")
        self.assertTrue(result.response)


if __name__ == "__main__":
    unittest.main()
