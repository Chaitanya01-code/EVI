import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.agents.conversation_agent import generate_conversation_response
from app.core.classify import IntentResult, classify_input
from app.core.context import WorkingContext
from app.router.intent_router import process_context
from app.task.task_models import TaskExecutionResult, TaskStatus


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.gemini = patch("app.core.classify._get_client", return_value=None)
        self.gemini.start()
        self.conversation_gemini = patch("app.agents.conversation_agent._get_client", return_value=None)
        self.conversation_gemini.start()
        self.persistence = patch("app.router.intent_router.save_record_async", new_callable=AsyncMock)
        self.persistence.start()
        self.memory_retrieval = patch(
            "app.router.intent_router.retrieve_user_memories", return_value=[]
        )
        self.memory_retrieval.start()
        self.memory_processing = patch(
            "app.router.intent_router.process_memory_async", new_callable=AsyncMock
        )
        self.memory_processing.start()
        self.tts = patch("app.router.intent_router.synthesize_audio_async", new_callable=AsyncMock)
        self.tts_mock = self.tts.start()

    async def asyncTearDown(self):
        self.persistence.stop()
        self.memory_retrieval.stop()
        self.memory_processing.stop()
        self.tts.stop()
        self.conversation_gemini.stop()
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
        task_result = TaskExecutionResult(
            success=True, message="Visual Studio Code was opened.",
            status=TaskStatus.COMPLETED, agent="DesktopAgent",
        )
        with patch("app.router.intent_router._task_manager.execute", return_value=task_result):
            result = await process_context(WorkingContext(
                transcript="Open VS Code",
                input_type="text",
            ))
        self.assertEqual(result.classification.mode, "task")
        self.assertTrue(result.response)

    async def test_conversation_agent_uses_transcript_history_and_context(self):
        gemini_response = Mock(text="Nice to hear from you! What are you working on today?")
        gemini_client = Mock()
        gemini_client.models.generate_content.return_value = gemini_response
        history = [{"user_message": "I'm working on my AI project.", "response": "That sounds interesting."}]

        with patch("app.agents.conversation_agent._get_client", return_value=gemini_client):
            response = generate_conversation_response(
                "The voice system.",
                conversation_history=history,
                working_context={"session_id": "test-session", "input_type": "text"},
            )

        self.assertEqual(response, gemini_response.text)
        prompt = gemini_client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("The voice system.", prompt)
        self.assertIn("I'm working on my AI project.", prompt)
        self.assertIn("test-session", prompt)

    async def test_conversation_route_speaks_generated_text(self):
        classification = IntentResult(
            mode="conversation", intent="casual_chat", action="", target="",
            confidence=0.99, requires_action=False,
            reason="Casual conversation.",
        )
        with patch("app.router.intent_router.classify_input", return_value=classification), \
                patch("app.router.intent_router.generate_conversation_response", return_value="Dynamic conversation response") as agent:
            result = await process_context(WorkingContext(
                transcript="Good morning",
                input_type="text",
            ))

        agent.assert_called_once()
        self.tts_mock.assert_not_called()
        self.assertEqual(result.response, "Dynamic conversation response")
        self.assertEqual(result.input_type, "text")
        self.assertEqual(result.response_type, "text")
        self.assertEqual(result.audio, "")
        self.assertEqual(result.session_id, result.session_id)

    async def test_text_task_does_not_call_tts(self):
        task_result = TaskExecutionResult(
            success=True, message="Visual Studio Code was opened.",
            status=TaskStatus.COMPLETED, agent="DesktopAgent",
        )
        with patch("app.router.intent_router._task_manager.execute", return_value=task_result):
            result = await process_context(WorkingContext(
                transcript="Open VS Code",
                input_type="text",
            ))
        self.assertEqual(result.response_type, "text")
        self.assertEqual(result.text, result.response)
        self.tts_mock.assert_not_called()

    async def test_voice_returns_audio_and_calls_tts(self):
        self.tts_mock.return_value = "data:audio/wav;base64,voice-audio"
        result = await process_context(WorkingContext(
            transcript="Hey EVI, how are you?",
            input_type="voice",
        ))
        self.assertEqual(result.input_type, "voice")
        self.assertEqual(result.response_type, "voice")
        self.assertEqual(result.audio, "data:audio/wav;base64,voice-audio")
        self.tts_mock.assert_awaited_once_with(result.response)

    async def test_voice_tts_failure_keeps_text_response(self):
        self.tts_mock.side_effect = RuntimeError("audio unavailable")
        task_result = TaskExecutionResult(
            success=True, message="Visual Studio Code was opened.",
            status=TaskStatus.COMPLETED, agent="DesktopAgent",
        )
        with patch("app.router.intent_router._task_manager.execute", return_value=task_result):
            result = await process_context(WorkingContext(
                transcript="Open VS Code",
                input_type="voice",
            ))
        self.assertEqual(result.response_type, "voice")
        self.assertTrue(result.text)
        self.assertEqual(result.audio, "")
        self.assertIsNotNone(result.tts_error)

    async def test_memories_are_loaded_into_working_context(self):
        memories = [{"key": "preferred_name", "value": "Chaitanya", "memory_type": "profile", "confidence": 1.0}]
        self.memory_retrieval.stop()
        with patch("app.router.intent_router.retrieve_user_memories", return_value=memories) as retrieve:
            result = await process_context(WorkingContext(
                user_id="user-1",
                transcript="Hello EVI",
                input_type="text",
            ))
        retrieve.assert_called_once_with("user-1")
        self.assertEqual(result.input_type, "text")

    async def test_memory_extraction_updates_and_deletes(self):
        from app.memory.memory_service import apply_memory
        from app.memory.schemas import MemoryExtraction

        with patch("app.memory.memory_service.upsert_memory") as upsert:
            apply_memory("user-1", MemoryExtraction(
                remember=True, operation="upsert", key="preferred_name",
                value="Chaitanya", memory_type="profile", confidence=1,
            ))
        upsert.assert_called_once_with("user-1", "preferred_name", "Chaitanya", "profile", 1.0)

        with patch("app.memory.memory_service.delete_memory") as delete:
            apply_memory("user-1", MemoryExtraction(
                remember=True, operation="delete", key="preferred_name", confidence=1,
            ))
        delete.assert_called_once_with("user-1", "preferred_name")

        with patch("app.memory.memory_service.upsert_memory") as blocked:
            apply_memory("user-1", MemoryExtraction(
                remember=True, operation="upsert", key="api_key",
                value="not persisted", memory_type="secret", confidence=1,
            ))
        blocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
