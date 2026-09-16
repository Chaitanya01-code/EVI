import unittest
from typing import Any, Dict

from app.agents.base.base_agent import BaseAgent
from app.orchestrator.orchestrator import MultiAgentOrchestrator
from app.task.task_models import StructuredTask, TaskExecutionResult, TaskStatus, TaskType
from app.task.task_router import AgentRegistry, TaskRouter
from app.task.task_understanding import understand_task
from unittest.mock import patch


class RecordingAgent(BaseAgent):
    def __init__(self, name: str, calls: list, fail_once: bool = False):
        self.name = name
        self.calls = calls
        self.fail_once = fail_once
        self.attempts = 0

    def plan(self, task: StructuredTask) -> Dict[str, Any]:
        return {"operation": task.action, "target": task.target}

    def execute(self, task: StructuredTask, plan: Dict[str, Any]) -> TaskExecutionResult:
        self.attempts += 1
        self.calls.append((self.name, task.action, task.target))
        if self.fail_once and self.attempts == 1:
            return TaskExecutionResult(
                success=False, message="temporary failure", status=TaskStatus.FAILED,
                agent=self.name, task=task,
            )
        return TaskExecutionResult(
            success=True, verified=True, message=f"{self.name} completed {task.action}",
            status=TaskStatus.COMPLETED, agent=self.name, task=task,
            output={"project_path": "C:/Projects/demo"} if task.action == "create_project" else {},
        )

    def verify(self, task: StructuredTask, result: TaskExecutionResult) -> TaskExecutionResult:
        return result


class OrchestratorTests(unittest.TestCase):
    def _task(self, steps):
        return StructuredTask(
            user_id="user-1", session_id="session-1", input_type="text",
            original_text="test workflow", task_type=TaskType.MULTI_STEP,
            category="orchestration", action="multi_step", steps=steps,
        )

    def _router(self, calls, fail_once=False):
        registry = AgentRegistry()
        registry.register(TaskType.DESKTOP, RecordingAgent("desktop", calls))
        registry.register(TaskType.CODING, RecordingAgent("coding", calls, fail_once=fail_once))
        registry.register(TaskType.BROWSER, RecordingAgent("browser", calls))
        registry.register(TaskType.CLOUD, RecordingAgent("cloud", calls))
        return TaskRouter(registry)

    def test_sequential_steps_pass_context(self):
        calls = []
        task = self._task([
            {"task_type": "coding", "action": "create_project", "target": "demo"},
            {"task_type": "desktop", "action": "open_folder", "target": "{project_path}"},
        ])
        result = MultiAgentOrchestrator(self._router(calls)).run(task)
        self.assertTrue(result.success)
        self.assertEqual(calls[1], ("desktop", "open_folder", "C:/Projects/demo"))
        self.assertTrue(result.verified)

    def test_independent_steps_run_and_combine(self):
        calls = []
        task = self._task([
            {"task_type": "cloud", "action": "check_deployment", "target": "AWS", "depends_on": []},
            {"task_type": "browser", "action": "search", "target": "Docker", "depends_on": []},
        ])
        result = MultiAgentOrchestrator(self._router(calls)).run(task)
        self.assertTrue(result.success)
        self.assertEqual({call[0] for call in calls}, {"cloud", "browser"})

    def test_failed_dependency_skips_dependent_step(self):
        calls = []
        task = self._task([
            {"task_type": "coding", "action": "create_project", "target": "demo"},
            {"task_type": "browser", "action": "open_url", "target": "{project_path}"},
        ])
        router = self._router(calls, fail_once=False)
        router.registry.get(TaskType.CODING).execute = lambda task, plan: TaskExecutionResult(
            success=False, message="permanent failure", status=TaskStatus.FAILED, agent="coding", task=task,
        )
        result = MultiAgentOrchestrator(router).run(task)
        self.assertFalse(result.success)
        self.assertEqual(len(calls), 0)
        self.assertEqual(result.output["steps"][1]["status"], "skipped")

    def test_failed_step_retries_with_bound(self):
        calls = []
        task = self._task([{"task_type": "coding", "action": "create_project", "target": "demo"}])
        result = MultiAgentOrchestrator(self._router(calls, fail_once=True)).run(task)
        self.assertTrue(result.success)
        self.assertEqual(len(calls), 2)

    def test_protected_step_waits_for_permission(self):
        calls = []
        task = self._task([{"task_type": "cloud", "action": "deploy", "target": "production"}])
        result = MultiAgentOrchestrator(self._router(calls)).run(task)
        self.assertFalse(result.success)
        self.assertEqual(result.status, TaskStatus.AWAITING_PERMISSION)
        self.assertEqual(calls, [])

    def test_requested_workflows_are_decomposed_by_operation(self):
        examples = {
            "Open VS Code, create a Python project, and run it.": ["desktop", "coding", "coding"],
            "Create a Python project, then open the project folder.": ["coding", "desktop"],
            "Open Chrome and search for FastAPI documentation.": ["desktop", "browser"],
            "Check AWS status and search the web for Docker documentation.": ["cloud", "browser"],
            "Create a Python project, install FastAPI, run it, and open its documentation.": ["coding", "coding", "coding", "browser"],
        }
        with patch("app.task.task_understanding._get_client", return_value=None):
            for text, expected in examples.items():
                with self.subTest(text=text):
                    result = understand_task(text)
                    self.assertEqual(result.task_type, TaskType.MULTI_STEP)
                    self.assertEqual([step.task_type for step in result.steps], expected)


if __name__ == "__main__":
    unittest.main()
