from whiteboard_mcp.errors import (
    evaluator_parse_failed,
    evaluator_timeout,
    internal_error,
    not_found,
)


def test_not_found():
    e = not_found("question", "slug", "made-up")
    assert e == {"error": "not_found", "entity": "question", "by": "slug", "value": "made-up"}


def test_evaluator_parse_failed():
    e = evaluator_parse_failed(raw="not json")
    assert e["error"] == "evaluator_parse_failed"
    assert e["raw"] == "not json"


def test_evaluator_timeout():
    e = evaluator_timeout()
    assert e == {"error": "evaluator_timeout"}


def test_internal_error():
    e = internal_error("boom")
    assert e == {"error": "internal_error", "message": "boom"}
