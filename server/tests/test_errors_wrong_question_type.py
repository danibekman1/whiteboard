"""Test for the wrong_question_type error helper.

Used by evaluate_sd_attempt to reject algo sessions, and by evaluate_attempt
(future PR) to reject SD sessions. Shape mirrors not_found and invalid_outcome:
discriminator + per-variant fields."""
from __future__ import annotations

from whiteboard_mcp.errors import wrong_question_type


def test_wrong_question_type_shape():
    err = wrong_question_type(got="algo", expected="system_design")
    assert err == {
        "error": "wrong_question_type",
        "got": "algo",
        "expected": "system_design",
    }


def test_wrong_question_type_serializable():
    """Cross-MCP-boundary requirement: must be JSON-serializable."""
    import json
    err = wrong_question_type(got="algo", expected="system_design")
    json.dumps(err)  # raises if not serializable
