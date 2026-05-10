"""Schema parity test: same fixture, both backends, same Pydantic shape.

Skipped in CI (no OAuth token); runs locally before merge to catch drift
between the metered and agent_sdk evaluator paths.
"""
from __future__ import annotations
import os

import pytest

from whiteboard_mcp import _evaluator_backend
from whiteboard_mcp.evaluator import EvaluatorOutput, SYSTEM_PROMPT, _build_user_message


REQUIRES_OAUTH = pytest.mark.skipif(
    not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="needs CLAUDE_CODE_OAUTH_TOKEN for agent_sdk backend",
)
REQUIRES_API = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="needs ANTHROPIC_API_KEY for metered backend",
)

FIXTURE_QUESTION = "Given an array, return two indices summing to a target."
FIXTURE_STEPS = [
    {"ordinal": 1, "description": "Clarify whether duplicates are allowed."},
    {"ordinal": 2, "description": "Propose a hash-map approach in O(n)."},
]
FIXTURE_USER_TEXT = "I'd use a hash map: scan once, store complements, look up target - x."


@REQUIRES_API
def test_metered_backend_returns_evaluator_output(monkeypatch):
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    out = _evaluator_backend.evaluate_with_forced_tool(
        system=SYSTEM_PROMPT,
        user_text=_build_user_message(FIXTURE_QUESTION, FIXTURE_STEPS, FIXTURE_USER_TEXT),
        output_schema=EvaluatorOutput,
        tool_name="submit_evaluation",
        model="claude-haiku-4-5-20251001",   # cheap; this is a parity fixture, not pedagogy
        client=None,
    )
    assert isinstance(out, EvaluatorOutput)
    assert out.suggested_move in {"nudge", "advance", "reanchor", "wrap_up"}


@REQUIRES_OAUTH
def test_agent_sdk_backend_returns_evaluator_output(monkeypatch):
    monkeypatch.setenv("CHAT_BACKEND", "agent_sdk")
    out = _evaluator_backend.evaluate_with_forced_tool(
        system=SYSTEM_PROMPT,
        user_text=_build_user_message(FIXTURE_QUESTION, FIXTURE_STEPS, FIXTURE_USER_TEXT),
        output_schema=EvaluatorOutput,
        tool_name="submit_evaluation",
        model="claude-haiku-4-5-20251001",
        client=None,
    )
    assert isinstance(out, EvaluatorOutput)
    assert out.suggested_move in {"nudge", "advance", "reanchor", "wrap_up"}
