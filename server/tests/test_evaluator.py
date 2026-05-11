from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from whiteboard_mcp.evaluator import (
    EVALUATOR_TIMEOUT_S,
    SYSTEM_PROMPT,
    EvaluatorOutput,
    evaluate,
)


def _fake_client(payload: dict):
    """Mimic anthropic.Anthropic().messages.create() returning a forced
    tool-use response with the given payload."""
    client = MagicMock()
    response = MagicMock()
    block = MagicMock(type="tool_use", input=payload)
    block.name = "submit_evaluation"
    response.content = [block]
    client.messages.create.return_value = response
    return client


def test_evaluate_parses_forced_tool_use():
    fake = _fake_client({
        "step_ordinal": 3,
        "correct": True,
        "missing": [],
        "suggested_move": "advance",
    })
    out = evaluate(
        client=fake,
        question_statement="Two Sum statement",
        canonical_steps=[{"ordinal": 1, "description": "..."}],
        user_text="hash map gives O(1) lookup",
    )
    assert isinstance(out, EvaluatorOutput)
    assert out.step_ordinal == 3
    assert out.correct is True
    assert out.suggested_move == "advance"
    assert out.missing == []


def test_evaluate_returns_missing_items_when_present():
    """The `missing` field must round-trip — regression: it was once dropped."""
    fake = _fake_client({
        "step_ordinal": 2,
        "correct": False,
        "missing": ["didn't mention the bottleneck", "no complexity claim"],
        "suggested_move": "nudge",
    })
    out = evaluate(
        client=fake, question_statement="Q", canonical_steps=[], user_text="x",
    )
    assert out.missing == ["didn't mention the bottleneck", "no complexity claim"]


def test_evaluate_raises_on_missing_tool_use():
    fake = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(type="text", text="oops no tool use")]
    fake.messages.create.return_value = response
    with pytest.raises(ValueError, match="no tool_use"):
        evaluate(
            client=fake,
            question_statement="...",
            canonical_steps=[],
            user_text="...",
        )


def test_evaluate_raises_on_pydantic_validation_failure():
    fake = _fake_client({
        "step_ordinal": "not-an-int",
        "correct": True,
        "missing": [],
        "suggested_move": "nudge",
    })
    with pytest.raises(ValidationError):
        evaluate(
            client=fake,
            question_statement="...",
            canonical_steps=[],
            user_text="...",
        )


def test_evaluate_passes_canonical_steps_with_ordinal_prefix():
    """The evaluator must see ordinal-prefixed steps; LLM parses depend on the format."""
    fake = _fake_client({
        "step_ordinal": 1,
        "correct": True,
        "missing": [],
        "suggested_move": "advance",
    })
    evaluate(
        client=fake,
        question_statement="Q",
        canonical_steps=[
            {"ordinal": 1, "description": "first step"},
            {"ordinal": 2, "description": "second step"},
        ],
        user_text="hi",
    )
    call_kwargs = fake.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "<canonical_steps>" in user_content
    assert "1. first step" in user_content
    assert "2. second step" in user_content


def test_evaluate_forces_submit_evaluation_tool():
    """Tool-choice must be forced; otherwise the model can ignore it."""
    fake = _fake_client({
        "step_ordinal": 1,
        "correct": True,
        "missing": [],
        "suggested_move": "advance",
    })
    evaluate(
        client=fake,
        question_statement="Q",
        canonical_steps=[],
        user_text="hi",
    )
    call_kwargs = fake.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_evaluation"}
    tool_names = [t["name"] for t in call_kwargs["tools"]]
    assert "submit_evaluation" in tool_names


def test_evaluate_includes_system_prompt_and_timeout():
    """SYSTEM_PROMPT and timeout must be wired into the create() call."""
    fake = _fake_client({
        "step_ordinal": 1,
        "correct": True,
        "missing": [],
        "suggested_move": "advance",
    })
    evaluate(
        client=fake,
        question_statement="Q",
        canonical_steps=[],
        user_text="hi",
    )
    call_kwargs = fake.messages.create.call_args.kwargs
    assert call_kwargs["system"] == SYSTEM_PROMPT
    assert call_kwargs["timeout"] == EVALUATOR_TIMEOUT_S


def test_evaluate_uses_explicit_model_arg_over_env(monkeypatch):
    """Explicit model arg wins over CLAUDE_COACH_MODEL env."""
    monkeypatch.setenv("CLAUDE_COACH_MODEL", "from-env")
    fake = _fake_client({
        "step_ordinal": 1,
        "correct": True,
        "missing": [],
        "suggested_move": "advance",
    })
    evaluate(
        client=fake,
        question_statement="Q",
        canonical_steps=[],
        user_text="hi",
        model="explicit-model",
    )
    assert fake.messages.create.call_args.kwargs["model"] == "explicit-model"


def test_evaluate_falls_back_to_env_model(monkeypatch):
    monkeypatch.setenv("CLAUDE_COACH_MODEL", "env-model")
    fake = _fake_client({
        "step_ordinal": 1,
        "correct": True,
        "missing": [],
        "suggested_move": "advance",
    })
    evaluate(
        client=fake,
        question_statement="Q",
        canonical_steps=[],
        user_text="hi",
    )
    assert fake.messages.create.call_args.kwargs["model"] == "env-model"


def test_get_anthropic_client_fails_fast_on_missing_key(monkeypatch):
    from whiteboard_mcp._anthropic import get_anthropic_client

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_anthropic_client()


def test_evaluate_accepts_none_client_on_agent_sdk_backend(monkeypatch):
    """The agent_sdk backend ignores `client` (it constructs its own SDK MCP
    server). The public signature must permit None to match runtime behavior
    in eval/run_eval.py, which passes client=None on that backend."""
    monkeypatch.setenv("CHAT_BACKEND", "agent_sdk")
    from whiteboard_mcp import evaluator as mod

    fixture = EvaluatorOutput(
        step_ordinal=1, correct=True, missing=[], suggested_move="advance",
    )
    monkeypatch.setattr(mod, "evaluate_with_forced_tool", lambda **kw: fixture)

    out = evaluate(
        client=None,
        question_statement="Q",
        canonical_steps=[],
        user_text="hi",
    )
    assert out is fixture
