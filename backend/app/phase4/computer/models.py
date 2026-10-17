from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComputerActionType(str, Enum):
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    TYPE = "TYPE"
    KEY = "KEY"
    HOTKEY = "HOTKEY"
    SCROLL = "SCROLL"
    MOVE = "MOVE"
    DRAG = "DRAG"
    WAIT = "WAIT"
    SCREENSHOT = "SCREENSHOT"


class ComputerAction(BaseModel):
    action_type: ComputerActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout: float = Field(default=10.0, gt=0, le=60.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComputerActionResult(BaseModel):
    success: bool
    action: str
    message: str = ""
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ComputerElement(BaseModel):
    element_id: str
    role: str
    name: str = ""
    value: str = ""
    description: str = ""
    enabled: bool = True
    visible: bool = True
    focused: bool = False
    bounds: Dict[str, int] = Field(default_factory=dict)
    parent: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    application: str = ""
    window: str = ""
    interaction_methods: List[str] = Field(default_factory=list)


class ComputerInteractionResult(BaseModel):
    success: bool
    action: str
    target: str = ""
    application: str = ""
    verified: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
