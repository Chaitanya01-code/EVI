from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider: str
    model: str


PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MODEL_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "15"))
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

FALLBACK_MODELS: List[ModelConfig] = [
    ModelConfig(
        "NVIDIA Nemotron 3 Ultra Free",
        "openrouter",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
    ),

    ModelConfig(
        "Nex-N2.5-Pro Free",
        "openrouter",
        "nex-agi/nex-n2.5-pro:free",
    ),

    ModelConfig(
        "Qwen3 Coder 480B A35B Free",
        "openrouter",
        "qwen/qwen3-coder:free",
    ),

    ModelConfig(
        "Gemma 4 26B A4B Free",
        "openrouter",
        "google/gemma-4-26b-a4b-it:free",
    ),

    ModelConfig(
        "GPT-OSS 20B Free",
        "openrouter",
        "openai/gpt-oss-20b:free",
    ),
]
