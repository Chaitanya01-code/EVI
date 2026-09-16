from __future__ import annotations

from typing import Any, Callable, Dict

from app.agents.cloud.providers import provider_for


class CloudToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Dict[str, Any]]] = {
            "inspect": self.inspect,
            "inspect_resources": self.inspect,
            "check_deployment": self.deployment_status,
            "deployment_status": self.deployment_status,
            "deploy": self.deploy,
            "health": self.health,
            "logs": self.placeholder,
            "metrics": self.placeholder,
            "rollback": self.placeholder,
            "terraform": self.placeholder,
            "docker": self.placeholder,
        }

    def resolve(self, action: str) -> Callable[..., Dict[str, Any]] | None:
        return self._tools.get(action)

    def list_tools(self) -> list[str]:
        return sorted(self._tools)

    @staticmethod
    def inspect(provider: str = "mock", target: str = "") -> Dict[str, Any]:
        return provider_for(provider).inspect(target)

    @staticmethod
    def deployment_status(provider: str = "mock", target: str = "") -> Dict[str, Any]:
        return provider_for(provider).deployment_status(target)

    @staticmethod
    def deploy(provider: str = "mock", target: str = "") -> Dict[str, Any]:
        return provider_for(provider).deploy(target, dry_run=True)

    @staticmethod
    def health(provider: str = "mock", target: str = "") -> Dict[str, Any]:
        status = provider_for(provider).deployment_status(target)
        if status.get("success"):
            status["message"] = "Cloud health information is available from the configured provider adapter."
        return status

    @staticmethod
    def placeholder(*_: Any, **__: Any) -> Dict[str, Any]:
        return {"success": False, "verified": False, "message": "This cloud capability is an interface placeholder and is not enabled yet."}


cloud_tools = CloudToolRegistry()
