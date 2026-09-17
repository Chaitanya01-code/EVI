from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
