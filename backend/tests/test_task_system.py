import unittest
from unittest.mock import patch

from app.agents.browser.agent import BrowserAgent
from app.agents.cloud.agent import CloudAgent
from app.agents.coding.agent import CodingAgent
from app.agents.desktop.agent import DesktopAgent
from app.task.task_models import TaskType
from app.task.task_router import build_default_registry
from app.task.task_understanding import build_structured_task, understand_task
from app.task.task_manager import TaskManager
from app.task.task_router import TaskRouter


class TaskSystemTests(unittest.TestCase):
    def setUp(self):
        self.gemini = patch("app.task.task_understanding._get_client", return_value=None)
        self.gemini.start()

    def tearDown(self):
        self.gemini.stop()

    def test_requested_task_understanding_examples(self):
        examples = (
            ("Open VS Code.", TaskType.DESKTOP, "open_application", "Visual Studio Code"),
            ("Create a Python project.", TaskType.CODING, "create_project", ""),
            ("Search Google for Docker tutorials.", TaskType.BROWSER, "search_web", ""),
            ("Deploy my application to AWS.", TaskType.CLOUD, "deploy", ""),
        )
        for text, task_type, action, target in examples:
            with self.subTest(text=text):
                result = understand_task(text)
                self.assertEqual(result.task_type, task_type)
                self.assertEqual(result.action, action)
                self.assertEqual(result.target, target)

    def test_structured_task_preserves_context(self):
        task = build_structured_task(
            "Open VS Code", "user-1", "session-1", "voice"
        )
        self.assertEqual(task.input_type, "voice")
        self.assertEqual(task.user_id, "user-1")
        self.assertEqual(task.session_id, "session-1")

    def test_registry_contains_exactly_four_agents(self):
        registry = build_default_registry()
        self.assertEqual(registry.names(), {
            "desktop": "DesktopAgent",
            "coding": "CodingAgent",
            "cloud": "CloudAgent",
            "browser": "BrowserAgent",
        })

    def test_agents_are_independently_registered(self):
        registry = build_default_registry()
        self.assertIsInstance(registry.get(TaskType.DESKTOP), DesktopAgent)
        self.assertIsInstance(registry.get(TaskType.CODING), CodingAgent)
        self.assertIsInstance(registry.get(TaskType.CLOUD), CloudAgent)
        self.assertIsInstance(registry.get(TaskType.BROWSER), BrowserAgent)

    def test_unknown_task_does_not_execute(self):
        result = understand_task("Please do the mysterious thing")
        self.assertEqual(result.task_type, TaskType.UNKNOWN)

    def test_desktop_agent_opens_and_verifies_vs_code(self):
        registry = build_default_registry()
        task = build_structured_task("Open VS Code", "user-1", "session-1", "text")
        agent = registry.get(TaskType.DESKTOP)
        with patch("app.agents.desktop.executor.shutil.which", return_value="code.cmd"), \
                patch("app.agents.desktop.executor.subprocess.Popen"), \
                patch("app.agents.desktop.verifier.subprocess.run") as run:
            run.return_value.stdout = "Code.exe                 1234 Console"
            result = TaskManager(TaskRouter(registry)).execute(task)
        self.assertTrue(result.success)
        self.assertEqual(result.agent, "DesktopAgent")
        self.assertEqual(result.status.value, "completed")


if __name__ == "__main__":
    unittest.main()
