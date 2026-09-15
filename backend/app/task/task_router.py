from __future__ import annotations

from typing import Dict, Optional

from app.agents.base.base_agent import BaseAgent
from app.task.task_models import StructuredTask, TaskType


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[TaskType, BaseAgent] = {}

    def register(self, task_type: TaskType, agent: BaseAgent) -> None:
        self._agents[task_type] = agent

    def get(self, task_type: TaskType) -> Optional[BaseAgent]:
        return self._agents.get(task_type)

    def names(self) -> Dict[str, str]:
        return {task_type.value: agent.__class__.__name__ for task_type, agent in self._agents.items()}


class TaskRouter:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def route(self, task: StructuredTask) -> Optional[BaseAgent]:
        return self.registry.get(task.task_type)


def build_default_registry() -> AgentRegistry:
    from app.agents.browser.agent import BrowserAgent
    from app.agents.cloud.agent import CloudAgent
    from app.agents.coding.agent import CodingAgent
    from app.agents.desktop.agent import DesktopAgent

    registry = AgentRegistry()
    registry.register(TaskType.DESKTOP, DesktopAgent())
    registry.register(TaskType.CODING, CodingAgent())
    registry.register(TaskType.CLOUD, CloudAgent())
    registry.register(TaskType.BROWSER, BrowserAgent())
    return registry
