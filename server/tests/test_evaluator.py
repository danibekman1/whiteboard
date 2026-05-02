from unittest.mock import MagicMock

import pytest

from whiteboard_mcp.evaluator import EvaluatorOutput, evaluate


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
        "step_id": 3,
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
    assert out.step_id == 3
    assert out.correct is True
    assert out.suggested_move == "advance"


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
        "step_id": "not-an-int",
        "correct": True,
        "missing": [],
        "suggested_move": "nudge",
    })
    with pytest.raises(Exception):
        evaluate(
            client=fake,
            question_statement="...",
            canonical_steps=[],
            user_text="...",
        )


def test_evaluate_passes_canonical_steps_in_user_message():
    """The evaluator must see the steps; this is what makes it the inner LLM."""
    fake = _fake_client({
        "step_id": 1,
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
    assert "first step" in user_content
    assert "second step" in user_content
    assert "<canonical_steps>" in user_content


def test_evaluate_forces_submit_evaluation_tool():
    """Tool-choice must be forced; otherwise the model can ignore it."""
    fake = _fake_client({
        "step_id": 1,
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
