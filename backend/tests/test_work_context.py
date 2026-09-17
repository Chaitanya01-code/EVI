import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.work.context.context_engine import ContextEngine
from app.work.events.models import WorkEvent
from app.work.events.normalizer import normalize_event
from app.work.events.repository import WorkEventRepository


class WorkContextTests(unittest.TestCase):
    def test_event_normalization_for_vscode(self):
        sample = {
            "event_type": "file_modified",
            "source": "vscode",
            "project_name": "EVI",
            "workspace_path": "C:/Users/test/Projects/EVI",
            "file_path": "backend/app/models/router.py",
            "timestamp": "2026-09-17T12:00:00Z",
            "metadata": {"application": "VS Code"},
            "confidence": 1.0,
        }

        event = normalize_event(sample)
        self.assertIsInstance(event, WorkEvent)
        self.assertEqual(event.event_type, "file_modified")
        self.assertEqual(event.project_name, "EVI")
        self.assertEqual(event.file_path, "backend/app/models/router.py")
        self.assertGreaterEqual(event.confidence, 0.0)

    def test_event_persistence_round_trip(self):
        repo = WorkEventRepository()
        fake_connection = MagicMock()
        fake_cursor = fake_connection.cursor.return_value
        fake_cursor.fetchall.return_value = []
        fake_cursor.fetchone.return_value = (1,)

        with patch("app.work.events.repository.get_connection", return_value=fake_connection):
            event = WorkEvent(
                event_type="command_executed",
                source="terminal",
                project_name="EVI",
                workspace_path="C:/Projects/EVI",
                command="pytest -q",
                exit_code=1,
                output_summary="1 failed",
                timestamp=datetime.now(timezone.utc),
                confidence=0.96,
            )
            stored = repo.save_event(event)
            recent = repo.list_recent(project_name="EVI", limit=10)

        self.assertIsInstance(stored, WorkEvent)
        self.assertEqual(recent, [])
        fake_connection.__enter__.return_value.execute.assert_called()

    def test_context_engine_updates_project_application_and_file(self):
        engine = ContextEngine()
        events = [
            {"event_type": "application_opened", "source": "desktop", "application": "VS Code", "timestamp": "2026-09-17T10:00:00Z", "confidence": 0.99},
            {"event_type": "folder_opened", "source": "filesystem", "project_name": "EVI", "workspace_path": "C:/Projects/EVI", "timestamp": "2026-09-17T10:01:00Z", "confidence": 0.98},
            {"event_type": "file_opened", "source": "vscode", "project_name": "EVI", "file_path": "backend/app/router/intent_router.py", "timestamp": "2026-09-17T10:02:00Z", "confidence": 0.99},
            {"event_type": "file_modified", "source": "vscode", "project_name": "EVI", "file_path": "backend/app/router/intent_router.py", "timestamp": "2026-09-17T10:03:00Z", "confidence": 1.0},
        ]

        state = engine.build_state(events)
        self.assertEqual(state.project, "EVI")
        self.assertEqual(state.application, "VS Code")
        self.assertEqual(state.current_file, "backend/app/router/intent_router.py")

    def test_terminal_failure_sets_current_problem(self):
        engine = ContextEngine()
        events = [
            {"event_type": "command_started", "source": "terminal", "project_name": "EVI", "command": "pytest -q", "timestamp": "2026-09-17T10:00:00Z", "confidence": 0.98},
            {"event_type": "command_executed", "source": "terminal", "project_name": "EVI", "command": "pytest -q", "exit_code": 1, "output_summary": "1 failed in 2.1s", "timestamp": "2026-09-17T10:01:00Z", "confidence": 0.99},
        ]

        state = engine.build_state(events)
        self.assertIn("pytest", state.current_problem.lower())
        self.assertIn("failed", state.current_problem.lower())

    def test_git_branch_updates_current_branch(self):
        engine = ContextEngine()
        events = [{"event_type": "git_branch_changed", "source": "git", "project_name": "EVI", "branch": "feature/llm-fallback", "timestamp": "2026-09-17T09:15:00Z", "confidence": 1.0}]

        state = engine.build_state(events)
        self.assertEqual(state.branch, "feature/llm-fallback")

    def test_confidence_separates_observed_and_inferred(self):
        observed = {"event_type": "file_modified", "source": "vscode", "project_name": "EVI", "confidence": 1.0, "timestamp": "2026-09-17T10:00:00Z"}
        inferred = {"event_type": "user_decision", "source": "nova", "project_name": "EVI", "confidence": 0.72, "timestamp": "2026-09-17T10:00:00Z", "metadata": {"inferred": True, "value": "debugging the router"}}

        normal_observed = normalize_event(observed)
        normal_inferred = normalize_event(inferred)

        self.assertGreater(normal_observed.confidence, 0.9)
        self.assertLess(normal_inferred.confidence, 1.0)
        self.assertTrue(normal_inferred.metadata.get("inferred") or normal_inferred.metadata.get("value"))

    def test_event_ordering_and_deduplication(self):
        engine = ContextEngine()
        events = [
            {"event_type": "file_modified", "source": "vscode", "event_id": "a", "file_path": "a.py", "timestamp": "2026-09-17T10:00:00Z", "confidence": 1.0},
            {"event_type": "file_modified", "source": "vscode", "event_id": "a", "file_path": "a.py", "timestamp": "2026-09-17T10:00:00Z", "confidence": 1.0},
            {"event_type": "file_opened", "source": "vscode", "event_id": "b", "file_path": "b.py", "timestamp": "2026-09-17T10:05:00Z", "confidence": 1.0},
        ]

        deduped = engine._deduplicate(events)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0]["event_id"], "a")

    def test_privacy_redaction(self):
        raw = {
            "event_type": "command_executed",
            "source": "terminal",
            "project_name": "EVI",
            "command": "curl -H 'Authorization: Bearer abc123' https://example.com",
            "output_summary": "API key leaked",
            "timestamp": "2026-09-17T10:00:00Z",
            "confidence": 1.0,
        }

        event = normalize_event(raw)
        command = event.command or ""
        output = event.output_summary or ""
        self.assertNotIn("abc123", command)
        self.assertNotIn("Authorization", command)
        self.assertNotIn("API key leaked", output)


if __name__ == "__main__":
    unittest.main()
