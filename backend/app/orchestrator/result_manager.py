from __future__ import annotations

from typing import List

from app.orchestrator.models import AgentResult, ExecutionContext, StepStatus, TaskStep


class ResultManager:
    def record(self, step: TaskStep, result: AgentResult, context: ExecutionContext) -> None:
        step.status = result.status
        step.result = {
            "output": result.output,
            "artifacts": result.artifacts,
            "message": result.message,
            "agent_result": result,
        }
        step.error = result.error
        context.agent_results[step.step_id] = result
        context.variables.update(result.next_context)
        context.variables.update(result.output)
        context.artifacts.extend(result.artifacts)
        if result.error:
            context.errors.append(result.error)

    def summarize(self, steps: List[TaskStep]) -> str:
        completed = sum(step.status == StepStatus.COMPLETED for step in steps)
        failed = next((step for step in steps if step.status == StepStatus.FAILED), None)
        skipped = sum(step.status == StepStatus.SKIPPED for step in steps)
        if failed:
            return f"Multi-step multi-agent task stopped at {failed.step_id}: {failed.error or 'step failed.'}"
        if skipped:
            return f"Multi-agent task completed {completed} steps; {skipped} dependent steps were skipped."
        return f"Completed {completed} of {len(steps)} planned steps."
