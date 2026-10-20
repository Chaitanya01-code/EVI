#!/usr/bin/env python3
"""Export deduplicated intent logs into day-grouped train and validation sets."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = ROOT / "data" / "training"
EXPORT_DIR = TRAINING_DIR / "export"


def _intent(record: dict[str, Any]) -> Any:
    predicted = record.get("predicted")
    return predicted.get("intent") if isinstance(predicted, dict) else predicted


def load_records(training_dir: Path = TRAINING_DIR) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(training_dir.glob("intent_log_*.jsonl")):
        file_day = path.stem[len("intent_log_"):]
        try:
            date.fromisoformat(file_day)
        except ValueError as error:
            raise ValueError(f"Invalid date in training log filename: {path.name}") from error
        with path.open("r", encoding="utf-8") as source:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSON in {path}:{line_number}") from error
                key = (record.get("user_text", ""), json.dumps(_intent(record), sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                timestamp = record.get("ts")
                day = timestamp[:10] if isinstance(timestamp, str) and len(timestamp) >= 10 else file_day
                try:
                    date.fromisoformat(day)
                except ValueError:
                    day = file_day
                records.append((day, record))
    return records


def split_by_day(
    records: list[tuple[str, dict[str, Any]]],
    validation_fraction: float = 0.1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for day, record in records:
        grouped[day].append(record)
    if len(grouped) < 2:
        raise ValueError("At least two distinct logging days are required for a day-grouped split.")

    target = len(records) * validation_fraction
    days = sorted(grouped)
    random.Random(42).shuffle(days)
    validation_days: set[str] = set()
    validation_count = 0
    for day in days:
        candidate = validation_count + len(grouped[day])
        if abs(candidate - target) < abs(validation_count - target):
            validation_days.add(day)
            validation_count = candidate

    if not validation_days:
        validation_days.add(min(grouped, key=lambda day: len(grouped[day])))

    train = [record for day, group in grouped.items() if day not in validation_days for record in group]
    validation = [record for day, group in grouped.items() if day in validation_days for record in group]
    return train, validation


def export_dataset() -> tuple[int, int]:
    records = load_records()
    train, validation = split_by_day(records)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, partition in (("train.jsonl", train), ("val.jsonl", validation)):
        with (EXPORT_DIR / filename).open("w", encoding="utf-8") as output:
            for record in partition:
                output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return len(train), len(validation)


if __name__ == "__main__":
    train_count, validation_count = export_dataset()
    print(f"Exported {train_count} training and {validation_count} validation records to {EXPORT_DIR}")
