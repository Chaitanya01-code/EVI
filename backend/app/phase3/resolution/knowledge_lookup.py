from __future__ import annotations

from typing import Any, Dict, List, Optional


class KnowledgeLookup:
    def __init__(self) -> None:
        self.catalog = {
            "rag": ["Use document ingestion and chunking for retrieval.", "Prefer semantic or hybrid retrieval for large knowledge bases."],
            "vector_store": ["pgvector is a common PostgreSQL-backed option."],
            "deployment": ["Deployment choices should be confirmed by the user before execution."],
        }

    def lookup(self, task: Optional[Dict[str, Any]], question: str) -> List[str]:
        if not task:
            return []
        goal = str(task.get("goal") or "").lower()
        matches: List[str] = []
        for key, values in self.catalog.items():
            if key in goal or key in question.lower():
                matches.extend(values)
        return matches
