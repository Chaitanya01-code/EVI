from typing import Any, Dict


def verify_plan(plan: Dict[str, Any], execution: Dict[str, Any]) -> bool:
    return bool(execution.get("success") and execution.get("verified", False))
