from __future__ import annotations

import asyncio
import contextvars
import inspect
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from phase2.decision.engine import DecisionOutcome, evaluate_decision

from app.api.lab_events import lab_event_bus
from app.training.redact import redact


logger = logging.getLogger(__name__)
_BACKGROUND = ThreadPoolExecutor(max_workers=1, thread_name_prefix="evi-action-audit")
_PENDING_LOCK = threading.Lock()
_PENDING: dict[str, dict[str, Any]] = {}
_APPROVAL_SCOPE: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "evi_approved_execution", default=False
)
_ROOT = Path(__file__).resolve().parents[3]
KILL_SWITCH_FILE = _ROOT / "data" / "kill_switch"
AUDIT_DIR = _ROOT / "data" / "audit"
_DEFAULT_TIMEOUT = 30.0


def _classify_risk(tool: str) -> str:
    normalized = tool.lower().replace("-", "_").replace(" ", "_")
    tool_name = normalized.rsplit(".", 1)[-1]
    if tool_name in {
        "list_dir", "search_files", "search_in_files", "file_info", "read_file",
        "open_file", "open_in_explorer", "search_file",
    }:
        return "low"
    if tool_name in {"create_file", "create_folder", "create_docx", "create_xlsx", "copy_file", "copy"}:
        return "medium"
    if tool_name in {
        "move_file", "move_folder", "rename_file", "rename_folder", "delete_file",
        "delete_folder", "bulk_copy", "bulk_move", "bulk_delete", "bulk_rename",
    }:
        return "high"
    if tool_name == "write_file":
        return "medium"
    if tool_name.startswith("bulk_"):
        return "high"
    if tool_name in {"force_close_app", "force_close"}:
        return "high"
    if tool_name in {"close_app", "open_app", "focus_app", "switch_window"}:
        return "medium"
    if tool_name in {"list_installed_apps", "list_running_apps", "find_app"}:
        return "low"
    high_terms = (
        "delete", "move_file", "move_folder", "overwrite", "kill", "force_close",
        "restart",
        "install", "setting", "commit", "push", "deploy", "shell",
        "run_command", "run_script", "shutdown", "rename", "write", "create",
        "copy", "rollback",
    )
    medium_terms = (
        "open_app", "open_application", "close_app", "focus", "switch_window", "type",
        "click", "mouse", "press_key", "hotkey", "drag", "resize_window",
        "minimize", "maximize", "computer_api",
    )
    low_terms = (
        "list", "read", "search", "screenshot", "status", "inspect", "find",
        "get_output",
    )
    if "move" in normalized and ("file" in normalized or "folder" in normalized):
        return "high"
    if any(term in normalized for term in high_terms):
        return "high"
    if any(term in normalized for term in medium_terms):
        return "medium"
    if any(term in normalized for term in low_terms):
        return "low"
    return "high"


def _kill_switch_enabled() -> bool:
    env_value = os.getenv("EVI_KILL_SWITCH", "").strip().lower()
    if env_value in {"1", "true", "yes", "on", "enabled"}:
        return True
    try:
        return KILL_SWITCH_FILE.exists()
    except OSError:
        logger.warning("Unable to inspect EVI kill-switch file", exc_info=True)
        return True


def _redact_params(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)[:500]
    if isinstance(value, dict):
        return {str(key)[:500]: _redact_params(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_params(item) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact(str(value))[:500]


def _audit_and_publish(event: dict[str, Any]) -> None:
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        path = AUDIT_DIR / f"actions_{event['ts'][:10]}.jsonl"
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception:
        logger.warning("Unable to append action audit record", exc_info=True)
    try:
        lab_event_bus.publish({
            "event": "action_attempted",
            "id": event["id"],
            "ts": event["ts"],
            "origin": event["origin"],
            "tool": event["tool"],
            "risk": event["risk"],
            "gate_verdict": event["gate_verdict"],
            "status": event["status"],
            "duration_ms": event["duration_ms"],
        })
    except Exception:
        logger.warning("Unable to publish action_attempted event", exc_info=True)


def _record_attempt(
    *,
    origin: str,
    tool: str,
    params: dict[str, Any],
    risk: str,
    gate_verdict: str,
    status: str,
    duration_ms: float,
    error: Optional[str],
) -> None:
    try:
        _BACKGROUND.submit(
            _prepare_audit_record,
            origin,
            tool,
            params,
            risk,
            gate_verdict,
            status,
            duration_ms,
            error,
        )
    except Exception:
        logger.warning("Unable to schedule action audit record", exc_info=True)


def _prepare_audit_record(
    origin: str,
    tool: str,
    params: dict[str, Any],
    risk: str,
    gate_verdict: str,
    status: str,
    duration_ms: float,
    error: Optional[str],
) -> None:
    try:
        try:
            redacted_params = _redact_params(params)
        except Exception:
            logger.warning("Unable to redact action audit parameters", exc_info=True)
            redacted_params = {}
        event = {
            "id": str(uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "origin": origin,
            "tool": tool,
            "params": redacted_params,
            "risk": risk,
            "gate_verdict": gate_verdict,
            "status": status,
            "duration_ms": duration_ms,
            "error": redact(error)[:500] if error else None,
        }
        _audit_and_publish(event)
    except Exception:
        logger.warning("Unable to prepare action audit record", exc_info=True)


def _approval_required(tool: str, risk: str, gate_approval_required: bool) -> bool:
    approved_tools = {
        value.strip().lower()
        for value in os.getenv("EVI_PREAPPROVED_TOOLS", "").split(",")
        if value.strip()
    }
    preapproved = tool.lower() in approved_tools
    return (
        gate_approval_required
        or risk == "high"
        or (risk == "medium" and not preapproved)
    ) and not _APPROVAL_SCOPE.get()


def _approval_summary(tool: str, params: dict[str, Any], risk: str, reason: str) -> str:
    target = params.get("target") or params.get("path") or params.get("application") or ""
    what = f"{tool}" + (f" targeting {redact(str(target))[:200]}" if target else "")
    impact = {
        "high": "This may make a significant or difficult-to-reverse system or data change.",
        "medium": "This will interact with the desktop or send input to an application.",
    }.get(risk, "This action is classified as requiring confirmation.")
    return f"What: {what}. Why: {reason or 'the action requires confirmation'}. Impact: {impact}"


def _timeout_seconds() -> float:
    try:
        return max(0.1, float(os.getenv("EVI_ACTION_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT))))
    except ValueError:
        logger.warning("Invalid EVI_ACTION_TIMEOUT_SECONDS; using default %s", _DEFAULT_TIMEOUT)
        return _DEFAULT_TIMEOUT


async def _run_action(run: Callable[[], Any], timeout: float) -> Any:
    async def invoke() -> Any:
        if inspect.iscoroutinefunction(run):
            return await run()
        loop = asyncio.get_running_loop()
        context = contextvars.copy_context()
        result = await loop.run_in_executor(None, context.run, run)
        if inspect.isawaitable(result):
            return await result
        return result

    return await asyncio.wait_for(invoke(), timeout=timeout)


async def guarded_execute(
    action: dict[str, Any],
    source: str,
    run: Callable[[], Any],
    *,
    _skip_approval: bool = False,
) -> dict[str, Any]:
    """Evaluate, authorize, execute, and audit one action."""
    started = time.monotonic()
    tool = str(action.get("tool") or "unknown")
    params = action.get("params") if isinstance(action.get("params"), dict) else {}
    risk = _classify_risk(tool)
    requested_risk = str(action.get("risk") or "").lower()
    severity = {"low": 0, "medium": 1, "high": 2}
    if requested_risk in severity and severity[requested_risk] > severity[risk]:
        risk = requested_risk
    verdict = "not_evaluated"
    status = "error"
    error_text: Optional[str] = None
    result: Any = None

    if _kill_switch_enabled():
        status = "blocked_kill_switch"
        verdict = "kill_switch_blocked"
        error_text = "Actions are disabled by the EVI kill switch."
        response = {"status": status, "result": None, "duration_ms": (time.monotonic() - started) * 1000, "error": error_text}
    else:
        try:
            decision = evaluate_decision(
                f"{tool} {json.dumps(params, ensure_ascii=False, default=str)}",
                context={"origin": source, "risk": risk},
            )
            verdict = decision.outcome.value
            if decision.outcome == DecisionOutcome.BLOCKED:
                status = "blocked_decision"
                error_text = decision.reason or "The Decision Gate blocked this action."
                response = {"status": status, "result": None, "duration_ms": (time.monotonic() - started) * 1000, "error": error_text}
            elif decision.outcome == DecisionOutcome.RESEARCH_REQUIRED:
                status = "blocked_decision"
                error_text = decision.reason or "The Decision Gate requires additional research."
                response = {"status": status, "result": None, "duration_ms": (time.monotonic() - started) * 1000, "error": error_text}
            elif _approval_required(tool, risk, decision.approval_required) and not _skip_approval:
                approval_id = str(uuid4())
                summary = _approval_summary(tool, params, risk, decision.reason)
                with _PENDING_LOCK:
                    expired_ids = [
                        key
                        for key, pending in _PENDING.items()
                        if pending["expires_at"] <= datetime.now(timezone.utc)
                    ]
                    for key in expired_ids:
                        _PENDING.pop(key, None)
                    _PENDING[approval_id] = {
                        "action": dict(action),
                        "source": source,
                        "run": run,
                        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
                    }
                status = "needs_approval"
                response = {
                    "status": status,
                    "result": None,
                    "duration_ms": (time.monotonic() - started) * 1000,
                    "approval_id": approval_id,
                    "summary": summary,
                }
            else:
                token = _APPROVAL_SCOPE.set(True) if _skip_approval else None
                try:
                    result = await _run_action(run, _timeout_seconds())
                    status = "ok"
                    response = {"status": status, "result": result, "duration_ms": (time.monotonic() - started) * 1000}
                except asyncio.TimeoutError:
                    status = "timeout"
                    error_text = "Action timed out."
                    response = {"status": status, "result": None, "duration_ms": (time.monotonic() - started) * 1000, "error": error_text}
                except Exception as error:
                    status = "error"
                    error_text = str(error)
                    response = {"status": status, "result": None, "duration_ms": (time.monotonic() - started) * 1000, "error": error_text}
                finally:
                    if token is not None:
                        _APPROVAL_SCOPE.reset(token)
        except Exception as error:
            status = "error"
            error_text = str(error)
            logger.exception("Decision Gate failed while evaluating action %s", tool)
            response = {"status": status, "result": None, "duration_ms": (time.monotonic() - started) * 1000, "error": error_text}

    _record_attempt(
        origin=source,
        tool=tool,
        params=params,
        risk=risk,
        gate_verdict=verdict,
        status=status,
        duration_ms=float(response["duration_ms"]),
        error=error_text,
    )
    return response


async def resolve_approval(approval_id: str, approve: bool) -> dict[str, Any]:
    with _PENDING_LOCK:
        pending = _PENDING.pop(approval_id, None)
    if pending is None:
        return {"status": "not_found"}
    if pending["expires_at"] <= datetime.now(timezone.utc):
        return {"status": "expired"}
    if not approve:
        return {"status": "rejected"}
    return await guarded_execute(
        pending["action"],
        pending["source"],
        pending["run"],
        _skip_approval=True,
    )


def run_guarded_sync(
    action: dict[str, Any],
    source: str,
    run: Callable[[], Any],
    *,
    _skip_approval: bool = False,
) -> dict[str, Any]:
    """Synchronous bridge used by existing synchronous agent/tool interfaces."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(guarded_execute(action, source, run, _skip_approval=_skip_approval))

    result: list[dict[str, Any]] = []
    failure: list[BaseException] = []

    def execute() -> None:
        try:
            result.append(asyncio.run(guarded_execute(action, source, run, _skip_approval=_skip_approval)))
        except BaseException as error:
            failure.append(error)

    thread = threading.Thread(target=execute, name="evi-guarded-sync", daemon=True)
    thread.start()
    thread.join()
    if failure:
        raise failure[0]
    return result[0]


def run_guarded_tool_sync(
    tool: str,
    params: dict[str, Any],
    source: str,
    run: Callable[[], Any],
    *,
    risk: Optional[str] = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {"tool": tool, "params": params}
    if risk:
        action["risk"] = risk
    gate_result = run_guarded_sync(
        action,
        source,
        run,
    )
    if gate_result["status"] == "ok":
        result = gate_result.get("result")
        return result if isinstance(result, dict) else {
            "success": True,
            "verified": True,
            "message": str(result),
        }
    message = gate_result.get("summary") or gate_result.get("error") or gate_result["status"]
    response = {
        "success": False,
        "verified": False,
        "message": message,
        "status": gate_result["status"],
    }
    if gate_result.get("approval_id"):
        response["approval_id"] = gate_result["approval_id"]
    return response


def set_kill_switch(enabled: bool) -> dict[str, Any]:
    if enabled:
        KILL_SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
        KILL_SWITCH_FILE.write_text("enabled\n", encoding="utf-8")
        os.environ["EVI_KILL_SWITCH"] = "true"
    else:
        KILL_SWITCH_FILE.unlink(missing_ok=True)
        os.environ.pop("EVI_KILL_SWITCH", None)
    return get_kill_switch_status()


def get_kill_switch_status() -> dict[str, bool]:
    return {"enabled": _kill_switch_enabled()}
