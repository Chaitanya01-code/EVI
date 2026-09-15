from typing import Any, Dict


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": False, "message": "The Browser Agent received the task, but browser execution is not enabled yet."}
