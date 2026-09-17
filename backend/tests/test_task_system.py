import unittest
from unittest.mock import patch

from app.agents.browser.agent import BrowserAgent
from app.agents.cloud.agent import CloudAgent
from app.agents.coding.agent import CodingAgent
from app.agents.desktop.agent import DesktopAgent
from app.task.task_models import AgentStatus, TaskStatus, TaskType
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
            ("Open VS Code.", TaskType.DESKTOP, "applications", "open_app", "Visual Studio Code"),
            ("Open Chrome.", TaskType.DESKTOP, "applications", "open_app", "Chrome"),
            ("Open Notepad.", TaskType.DESKTOP, "applications", "open_app", "Notepad"),
            ("Open Calculator.", TaskType.DESKTOP, "applications", "open_app", "Calculator"),
            ("Close Chrome.", TaskType.DESKTOP, "applications", "close_app", "Chrome"),
            ("Restart VS Code.", TaskType.DESKTOP, "applications", "restart_app", "Visual Studio Code"),
            ("Search Google for Docker tutorials.", TaskType.BROWSER, "navigation", "search", "Docker tutorials"),
            ("Open a website.", TaskType.BROWSER, "navigation", "navigate", "website"),
            ("Search the web for Python.", TaskType.BROWSER, "navigation", "search", "Python"),
            ("Create a Python project.", TaskType.CODING, "development", "create_project", ""),
            ("Debug this Python code.", TaskType.CODING, "development", "debug_code", ""),
            ("Create a FastAPI application.", TaskType.CODING, "development", "create_project", ""),
            ("Deploy my application to AWS.", TaskType.CLOUD, "deployment", "deploy", "AWS"),
            ("Check my Docker deployment.", TaskType.CLOUD, "deployment", "check_deployment", "Docker"),
        )
        for text, task_type, category, action, target in examples:
            with self.subTest(text=text):
                result = understand_task(text)
                self.assertEqual(result.task_type, task_type)
                self.assertEqual(result.category, category)
                self.assertEqual(result.action, action)
                self.assertEqual(result.target, target)

    def test_multi_step_edge_case(self):
        result = understand_task("Open Chrome and search Google for Docker tutorials.")
        self.assertEqual(result.task_type, TaskType.MULTI_STEP)
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.steps[0]["task_type"], "desktop")
        self.assertEqual(result.steps[0]["action"], "open_app")
        self.assertEqual(result.steps[0]["target"], "Chrome")
        self.assertEqual(result.steps[1]["task_type"], "browser")
        self.assertEqual(result.steps[1]["action"], "search")
        self.assertEqual(result.steps[1]["target"], "Docker tutorials")

    def test_multi_step_task_manager_safely_rejects_without_crashing(self):
        registry = build_default_registry()
        task = build_structured_task("Open Chrome and search Google for Docker tutorials.", "user-1", "session-1", "text")
        result = TaskManager(TaskRouter(registry)).execute(task)
        self.assertTrue(result.success)
        self.assertIn("completed", result.message.lower())
        self.assertEqual(result.agent, "orchestrator")

    def test_complex_multi_step_commands_decompose_into_goal_steps(self):
        result = understand_task("Open Chrome, go to YouTube, search for Python tutorials, and open the first video.")
        self.assertEqual(result.task_type, TaskType.MULTI_STEP)
        self.assertGreaterEqual(len(result.steps), 4)
        steps = [step["action"] for step in result.steps]
        self.assertIn("open_app", steps)
        self.assertIn("navigate", steps)
        self.assertIn("search", steps)

    def test_complex_multi_step_commands_reference_the_first_search_result_url(self):
        result = understand_task("Open Chrome, go to YouTube, search for Python tutorials, and open the first video.")
        self.assertEqual(result.steps[-1]["target"], "{results[0].url}")

    def test_independent_tasks_remain_parallel_when_not_dependent(self):
        result = understand_task("Open Chrome and Calculator at the same time.")
        self.assertEqual(result.task_type, TaskType.MULTI_STEP)
        self.assertGreaterEqual(len(result.steps), 2)
        self.assertTrue(all(step.get("depends_on", []) == [] for step in result.steps))

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
        from app.agents.desktop.applications import Application
        registry = build_default_registry()
        task = build_structured_task("Open VS Code", "user-1", "session-1", "text")
        agent = registry.get(TaskType.DESKTOP)
        app = Application("Visual Studio Code", "code.cmd", "Code.exe")
        with patch("app.agents.desktop.applications.open_app.find_app", return_value=app), \
                patch("subprocess.Popen"), \
                patch("app.agents.desktop.verifier.subprocess.run") as run:
            run.return_value.stdout = "Code.exe                 1234 Console"
            result = TaskManager(TaskRouter(registry)).execute(task)
        self.assertTrue(result.success)
        self.assertEqual(result.agent, "DesktopAgent")
        self.assertEqual(result.status.value, "completed")

    def test_status_and_agent_state_are_separate(self):
        self.assertEqual(TaskStatus.RUNNING.value, "running")
        self.assertEqual(TaskStatus.VERIFICATION.value, "verification")
        self.assertEqual(AgentStatus.UNASSIGNED.value, "unassigned")
        self.assertEqual(AgentStatus.ASSIGNED.value, "assigned")

    def test_equivalent_open_vs_code_tasks_are_deduplicated(self):
        manager = TaskManager(TaskRouter(build_default_registry()))
        task = build_structured_task("Open Visual Studio Code", "user-1", "session-1", "text")
        self.assertTrue(hasattr(manager, "is_equivalent_active_task"))
        self.assertFalse(manager.is_equivalent_active_task(task))


if __name__ == "__main__":
    unittest.main()
