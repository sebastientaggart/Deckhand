"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging

from deckhand.logging_config import JsonFormatter, configure_logging


def _make_record(**kwargs) -> logging.LogRecord:
    record = logging.LogRecord(
        name="deckhand.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    for key, value in kwargs.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_required_fields() -> None:
    record = _make_record()
    out = json.loads(JsonFormatter().format(record))
    assert out["level"] == "INFO"
    assert out["logger"] == "deckhand.test"
    assert out["message"] == "hello world"
    assert "timestamp" in out


def test_json_formatter_includes_extra_context() -> None:
    record = _make_record(agent_id="mock-1", action_name="run", client_ip="127.0.0.1")
    out = json.loads(JsonFormatter().format(record))
    assert out["agent_id"] == "mock-1"
    assert out["action_name"] == "run"
    assert out["client_ip"] == "127.0.0.1"


def test_configure_logging_is_idempotent_and_sets_level() -> None:
    configure_logging(level="DEBUG", fmt="json")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    handlers_before = len(root.handlers)
    assert handlers_before == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)

    # Re-configuring replaces handlers, doesn't accumulate them
    configure_logging(level="WARNING", fmt="plain")
    assert len(root.handlers) == 1
    assert root.level == logging.WARNING
    assert not isinstance(root.handlers[0].formatter, JsonFormatter)
