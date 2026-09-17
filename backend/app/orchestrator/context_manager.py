from __future__ import annotations

import re
from typing import Any, Dict

from app.orchestrator.models import ExecutionContext, TaskStep


_TOKEN = re.compile(r"\{([A-Za-z0-9_.\-\[\]]+)\}")


class ContextManager:
    def _resolve_path(self, current: Any, path: str) -> Any:
        for token in re.findall(r"[A-Za-z0-9_-]+|\[\d+\]", path):
            if token.startswith("["):
                index = int(token[1:-1])
                if not isinstance(current, list):
                    return ""
                if not (0 <= index < len(current)):
                    return ""
                current = current[index]
                continue
            if isinstance(current, dict):
                current = current.get(token, "")
            elif hasattr(current, token):
                current = getattr(current, token)
            else:
                return ""
        return current

    def resolve_value(self, value: Any, context: ExecutionContext) -> Any:
        if isinstance(value, str):
            def replace(match: re.Match[str]) -> str:
                return str(self._resolve_path(context.variables, match.group(1)))
            return _TOKEN.sub(replace, value)
        if isinstance(value, dict):
            return {key: self.resolve_value(item, context) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve_value(item, context) for item in value]
        return value

    def prepare_step(self, step: TaskStep, context: ExecutionContext) -> TaskStep:
        step.target = self.resolve_value(step.target, context)
        step.arguments = self.resolve_value(step.arguments, context)
        return step

    def merge_result(self, context: ExecutionContext, step: TaskStep) -> None:
        context.agent_results[step.step_id] = step.result.get("agent_result")
        output = step.result.get("output", {})
        if isinstance(output, dict):
            context.variables.update(output)
        context.artifacts.extend(step.result.get("artifacts", []))
        if step.error:
            context.errors.append(step.error)
