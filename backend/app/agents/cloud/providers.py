from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict


class CloudProvider(ABC):
    name = "unknown"

    @abstractmethod
    def inspect(self, target: str = "") -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def deployment_status(self, target: str = "") -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def deploy(self, target: str = "", dry_run: bool = True) -> Dict[str, Any]:
        raise NotImplementedError


class UnconfiguredProvider(CloudProvider):
    def __init__(self, name: str) -> None:
        self.name = name

    def inspect(self, target: str = "") -> Dict[str, Any]:
        return {"success": False, "verified": False, "message": f"{self.name.upper()} credentials are not configured for EVI."}

    def deployment_status(self, target: str = "") -> Dict[str, Any]:
        return {"success": False, "verified": False, "message": f"No {self.name.upper()} deployment adapter is configured."}

    def deploy(self, target: str = "", dry_run: bool = True) -> Dict[str, Any]:
        return {"success": False, "verified": False, "message": "Real cloud deployment is disabled until an authorized provider adapter is configured."}


class MockProvider(CloudProvider):
    name = "mock"

    def inspect(self, target: str = "") -> Dict[str, Any]:
        return {"success": True, "verified": True, "message": "Mock cloud resources inspected.", "provider": self.name, "resources": []}

    def deployment_status(self, target: str = "") -> Dict[str, Any]:
        return {"success": True, "verified": True, "message": "No mock deployment is active.", "provider": self.name, "status": "not_deployed"}

    def deploy(self, target: str = "", dry_run: bool = True) -> Dict[str, Any]:
        return {"success": True, "verified": True, "message": "Deployment plan created in dry-run mode; no cloud resources were changed.", "provider": self.name, "dry_run": True, "target": target}


def provider_for(name: str) -> CloudProvider:
    normalized = name.lower().strip()
    if normalized == "mock" or os.getenv("EVI_CLOUD_DRY_RUN", "1") == "1":
        return MockProvider()
    if normalized in {"aws", "azure", "gcp"}:
        return UnconfiguredProvider(normalized)
    return UnconfiguredProvider("unknown")
