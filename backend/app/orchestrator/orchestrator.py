from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.orchestrator.coordinator import Coordinator
from app.orchestrator.executor import PlanExecutor
from app.orchestrator.models import ExecutionContext, OrchestrationResult, StepStatus
from app.orchestrator.planner import build_plan
from app.orchestrator.result_manager import ResultManager
from app.orchestrator.verifier import OrchestrationVerifier
from app.task.task_models import StructuredTask, TaskExecutionResult, TaskStatus
from app.task.task_router import TaskRouter
from app.safety.executor_gate import run_guarded_sync


class MultiAgentOrchestrator:
    def __init__(self, router: TaskRouter, event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.router = router
        self.event_callback = event_callback
        self.verifier = OrchestrationVerifier()
        self.result_manager = ResultManager()

    def run(self, task: StructuredTask) -> TaskExecutionResult:
        file_actions = {
            "open_file", "copy_file", "move_file", "rename_file", "delete_file", "search_file",
            "list_dir", "search_files", "search_in_files", "file_info", "read_file", "create_file",
            "write_file", "create_docx", "create_xlsx", "open_in_explorer", "bulk_file_operation",
            "create_folder", "open_folder", "rename_folder", "move_folder", "delete_folder",
        }
        has_tool_gated_file_step = task.task_type.value == "multi_step" and any(
            step.get("category") in {"files", "folders"} or step.get("action") in file_actions
            for step in task.steps
        )
        if has_tool_gated_file_step:
            return self._run(task)
        gated = run_guarded_sync(
            {
                "tool": task.action or "multi_step",
                "params": {"target": task.target, "task_type": task.task_type.value},
            },
            "orchestrator",
            lambda: self._run(task),
        )
        if gated["status"] == "ok":
            return gated["result"]
        output = {"blocked": True, "gate_status": gated["status"]}
        if gated.get("approval_id"):
            output["approval_id"] = gated["approval_id"]
            output["approval_summary"] = gated.get("summary")
        task.status = TaskStatus.AWAITING_PERMISSION if gated["status"] == "needs_approval" else TaskStatus.BLOCKED
        return TaskExecutionResult(
            success=False,
            verified=False,
            message=gated.get("summary") or gated.get("error") or gated["status"],
            status=TaskStatus.AWAITING_PERMISSION if gated["status"] == "needs_approval" else TaskStatus.BLOCKED,
            agent="orchestrator",
            task=task,
            output=output,
        )

    def _run(self, task: StructuredTask) -> TaskExecutionResult:
        plan = build_plan(task)
        context = ExecutionContext(
            task_id=task.task_id,
            user_id=task.user_id,
            session_id=task.session_id,
            original_request=task.original_text,
            input_type=task.input_type,
            execution_state="executing",
        )
        coordinator = Coordinator(self.router, self.event_callback)
        steps = PlanExecutor(coordinator).run(plan, context)
        verified = self.verifier.verify_plan(steps)
        success = bool(steps) and all(step.status == StepStatus.COMPLETED for step in steps)
        message = self.result_manager.summarize(steps)
        context.execution_state = "completed" if success and verified else "failed"
        status = TaskStatus.COMPLETED if success and verified else TaskStatus.FAILED
        if any(step.status == StepStatus.WAITING for step in steps):
            status = TaskStatus.AWAITING_PERMISSION
        task.status = status
        return TaskExecutionResult(
            success=success and verified,
            verified=verified,
            message=message,
            status=status,
            agent="orchestrator",
            task=task,
            output={
                "steps": [step.model_dump() for step in steps],
                "events": context.events,
                "variables": context.variables,
            },
        )
