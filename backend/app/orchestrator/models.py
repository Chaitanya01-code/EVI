from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class TaskDependency(BaseModel):
    step_id: str
    required_status: StepStatus = StepStatus.COMPLETED


class TaskStep(BaseModel):
    step_id: str
    task_id: str
    description: str
    agent_type: str
    action: str
    target: str = ""
    arguments: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[TaskDependency] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class MultiTask(BaseModel):
    task_id: str
    user_id: str
    session_id: str
    original_request: str
    input_type: str
    steps: List[TaskStep] = Field(default_factory=list)


class AgentRequest(BaseModel):
    task_id: str
    step_id: str
    agent: str
    action: str
    target: str = ""
    arguments: Dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    task_id: str
    step_id: str
    agent: str
    action: str
    status: StepStatus
    success: bool
    verified: bool = False
    output: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    message: str = ""
    next_context: Dict[str, Any] = Field(default_factory=dict)


class ExecutionContext(BaseModel):
    task_id: str
    user_id: str
    session_id: str
    original_request: str
    input_type: str
    current_step: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    agent_results: Dict[str, AgentResult] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    execution_state: str = "planning"
    events: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    task_id: str
    steps: List[TaskStep]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrchestrationResult(BaseModel):
    success: bool
    verified: bool
    message: str
    status: StepStatus
    agent: str = "orchestrator"
    task_id: str
    steps: List[TaskStep] = Field(default_factory=list)
    context: Optional[ExecutionContext] = None
