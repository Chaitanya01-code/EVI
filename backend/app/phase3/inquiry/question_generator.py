from __future__ import annotations

from typing import Any, Dict, List

from app.phase3.inquiry.models import InquiryQuestion, QuestionCategory, QuestionPriority


class QuestionGenerator:
    def __init__(self) -> None:
        self.templates = {
            "rag": [
                {
                    "question": "What type of documents will this RAG system index and search?",
                    "category": QuestionCategory.missing_requirement,
                    "purpose": "The document type determines the ingest pipeline, chunking strategy, and storage choices.",
                    "priority": QuestionPriority.critical,
                },
                {
                    "question": "What retrieval approach is appropriate for this project: lexical, semantic, hybrid, or a custom pipeline?",
                    "category": QuestionCategory.technical_information,
                    "purpose": "The retrieval design affects indexing, latency, relevance quality, and architecture.",
                    "priority": QuestionPriority.high,
                },
                {
                    "question": "Which vector database or storage system is available in this project environment?",
                    "category": QuestionCategory.environment_information,
                    "purpose": "The project environment constrains the storage and retrieval implementation choices.",
                    "priority": QuestionPriority.critical,
                },
            ],
            "default": [
                {
                    "question": "What information is required to continue this task safely and correctly?",
                    "category": QuestionCategory.missing_requirement,
                    "purpose": "This clarifies the minimum facts needed to complete the task without guessing.",
                    "priority": QuestionPriority.required,
                }
            ],
        }

    def generate_questions(self, task: Dict[str, Any], known: List[str] | None = None) -> List[InquiryQuestion]:
        known_set = {item.lower() for item in (known or [])}
        goal = str(task.get("goal") or "").lower()
        templates = self.templates.get("rag", self.templates["default"]) if "rag" in goal else self.templates["default"]
        questions: List[InquiryQuestion] = []
        for item in templates:
            question_text = item["question"]
            normalized = question_text.lower()
            if any(term in normalized for term in ("vector database", "documents", "retrieval approach")) and any(term in known_set for term in ("vector_store", "rag", "documents", "retrieval")):
                continue
            q = InquiryQuestion(
                task_id=str(task.get("task_id") or "unknown-task"),
                question=question_text,
                purpose=item["purpose"],
                category=item["category"],
                priority=item["priority"],
                source="self_generated",
                importance=str(item["priority"]).lower(),
            )
            questions.append(q)
        return questions
