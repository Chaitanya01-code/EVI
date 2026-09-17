import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.agents.browser.tools import web_search
from app.agents.cloud.providers import MockProvider
from app.agents.coding.tools import create_file, run_command
from app.task.task_models import TaskType
from app.task.task_router import build_default_registry
from app.task.task_understanding import build_structured_task


class AgentFoundationTests(unittest.TestCase):
    def test_browser_search_returns_structured_results(self):
        source = '<a class="result__a" href="https://example.com">Example</a>'
        with patch("app.agents.browser.tools._fetch", return_value=source):
            result = web_search("Docker")
        self.assertTrue(result["success"])
        self.assertEqual(result["results"][0]["title"], "Example")

    def test_browser_search_matches_current_duckduckgo_markup(self):
        source = '''
        <a rel="nofollow" class="result-link" href="https://www.youtube.com/results?search_query=Python+tutorials">
            <span class="result-title">Python tutorials - YouTube</span>
        </a>
        '''
        with patch("app.agents.browser.tools._fetch", return_value=source):
            result = web_search("Python tutorials")
        self.assertTrue(result["success"])
        self.assertEqual(result["results"][0]["title"], "Python tutorials - YouTube")

    def test_coding_file_creation_and_command_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            result = create_file("main.py", "print('ok')", directory)
            self.assertTrue(result["success"])
            self.assertTrue(Path(directory, "main.py").exists())
            blocked = run_command("python -c print('ok'); del important", directory)
            self.assertFalse(blocked["success"])

    def test_cloud_provider_is_dry_run_and_non_destructive(self):
        result = MockProvider().deploy("demo", dry_run=True)
        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])

    def test_domain_tasks_route_to_existing_agent_registry(self):
        registry = build_default_registry()
        examples = (
            ("Search Google for Docker", TaskType.BROWSER, "BrowserAgent"),
            ("Create a Python project", TaskType.CODING, "CodingAgent"),
            ("Deploy my application to AWS", TaskType.CLOUD, "CloudAgent"),
        )
        for text, task_type, agent_name in examples:
            with self.subTest(text=text):
                task = build_structured_task(text, "user", "session", "text")
                self.assertEqual(task.task_type, task_type)
                self.assertEqual(registry.get(task_type).__class__.__name__, agent_name)


if __name__ == "__main__":
    unittest.main()