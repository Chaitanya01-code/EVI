import json
import logging
from pathlib import Path
from unittest.mock import patch

from app.core import classify
from app.training import intent_logger
from app.training.redact import redact


def test_redact_masks_keys_emails_and_phones():
    text = "api_key=secret-value contact jane.doe@example.com or +1 (415) 555-0123"
    result = redact(text)

    assert "secret-value" not in result
    assert "[REDACTED_KEY]" in result
    assert "[REDACTED_EMAIL]" in result
    assert "[REDACTED_PHONE]" in result


def test_redact_masks_long_email_as_a_single_value():
    result = redact("abcdefghijklmnopqrstuvwx@example.com")
    assert result == "[REDACTED_EMAIL]"


def test_redact_masks_api_tokens_and_long_strings():
    result = redact("sk-abc123 AIza123abc ghp_123abc Bearer access-token " + "a" * 24)

    assert "sk-abc123" not in result
    assert "AIza123abc" not in result
    assert "ghp_123abc" not in result
    assert "access-token" not in result
    assert "a" * 24 not in result


def test_redact_is_idempotent():
    once = redact("email jane@example.com, password=hunter2")
    assert redact(once) == once


def test_redact_leaves_normal_text_unchanged():
    text = "Please open the weather dashboard for me."
    assert redact(text) == text
    assert redact("The date is 2026-10-20.") == "The date is 2026-10-20."


def test_log_intent_writes_valid_jsonl(tmp_path):
    with patch.object(intent_logger, "TRAINING_DATA_DIR", tmp_path):
        record = intent_logger.log_intent(
            user_text="Email me at jane@example.com",
            context_summary={"input_type": "text"},
            source="text",
            classifier_used="gemini",
            predicted={"mode": "question", "intent": "general_question"},
            latency_ms=12.5,
        )

    assert record is not None
    log_files = list(tmp_path.glob("intent_log_*.jsonl"))
    assert len(log_files) == 1
    lines = log_files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    saved = json.loads(lines[0])
    assert saved["user_text"] == "Email me at [REDACTED_EMAIL]"
    assert saved["predicted"]["intent"] == "general_question"
    assert saved["feedback"] is None
    assert saved["outcome"] is None


def test_log_intent_never_raises_for_unwritable_path(caplog):
    with patch.object(intent_logger, "TRAINING_DATA_DIR", Path("NUL\\blocked")):
        with caplog.at_level(logging.WARNING):
            result = intent_logger.log_intent(
                user_text="hello",
                context_summary={},
                source="text",
                classifier_used="local_fallback",
                predicted={"intent": "casual_chat"},
                latency_ms=1,
            )

    assert result is None
    assert "Unable to append intent training record" in caplog.text


def test_log_intent_respects_opt_out_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("EVI_LOG_TRAINING_DATA", "false")
    with patch.object(intent_logger, "TRAINING_DATA_DIR", tmp_path):
        result = intent_logger.log_intent(
            user_text="hello",
            context_summary={},
            source="text",
            classifier_used="local_fallback",
            predicted={"intent": "casual_chat"},
            latency_ms=1,
        )

    assert result is None
    assert list(tmp_path.iterdir()) == []


def test_classifier_failure_logs_local_fallback_and_publishes_event():
    def run_submitted_task(callback, *args):
        callback(*args)

    with patch("app.core.classify.is_training_logging_enabled", return_value=True), \
            patch("app.core.classify._generate_llm", side_effect=RuntimeError("offline")), \
            patch.object(classify._training_executor, "submit", side_effect=run_submitted_task), \
            patch("app.core.classify.log_intent") as log_record, \
            patch.object(classify.lab_event_bus, "publish") as publish:
        result = classify.classify_input("What is the weather?", {"input_type": "voice"})

    assert result.intent == "general_question"
    assert log_record.call_args.kwargs["source"] == "voice"
    assert log_record.call_args.kwargs["classifier_used"] == "local_fallback"
    assert log_record.call_args.kwargs["error"] == "offline"
    assert publish.call_args.args[0]["event"] == "intent_classified"
    assert publish.call_args.args[0]["predicted"] == "general_question"
