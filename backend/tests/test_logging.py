# tests for app/core/logging.py — JSONFormatter and the request_id contextvar.
# no app, no db: pure logging.LogRecord construction.

import json
import logging

from app.core.logging import JSONFormatter, request_id_var


def make_record(msg="hello", **extra):
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_format_produces_valid_json_with_core_fields():
    payload = json.loads(JSONFormatter().format(make_record("hello world")))

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert "timestamp" in payload


def test_format_defaults_request_id_to_dash_outside_a_request():
    payload = json.loads(JSONFormatter().format(make_record()))
    assert payload["request_id"] == "-"


def test_format_includes_request_id_when_set():
    token = request_id_var.set("abc123")
    try:
        payload = json.loads(JSONFormatter().format(make_record()))
    finally:
        request_id_var.reset(token)

    assert payload["request_id"] == "abc123"


def test_format_includes_known_extra_fields_when_present():
    payload = json.loads(JSONFormatter().format(make_record(duration_ms=12.3, row_count=5)))

    assert payload["duration_ms"] == 12.3
    assert payload["row_count"] == 5


def test_format_includes_rate_limit_fields():
    payload = json.loads(JSONFormatter().format(make_record(client="1.2.3.4", retry_after=30)))

    assert payload["client"] == "1.2.3.4"
    assert payload["retry_after"] == 30


def test_format_omits_unset_extra_fields():
    payload = json.loads(JSONFormatter().format(make_record()))
    assert "duration_ms" not in payload
    assert "sql" not in payload
