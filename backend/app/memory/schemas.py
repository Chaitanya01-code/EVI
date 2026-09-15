from typing import Literal

from pydantic import BaseModel, Field


class MemoryExtraction(BaseModel):
    remember: bool = False
    operation: Literal["upsert", "delete", "none"] = "none"
    key: str = ""
    value: str = ""
    memory_type: str = "profile"
    confidence: float = Field(default=0, ge=0, le=1)
