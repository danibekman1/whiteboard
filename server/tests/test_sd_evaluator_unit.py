"""Unit tests for whiteboard_mcp.sd_evaluator.

Covers:
  - SDEvaluatorOutput Pydantic shape and field semantics
  - _build_user_message renders the question + phases + pushbacks + history
  - SUBMIT_TOOL has the right shape for Anthropic forced tool-use
  - evaluate() with a mocked Anthropic client returns parsed output
  - evaluate() raises ValueError when no tool_use block present
"""
from __future__ import annotations
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from whiteboard_mcp.sd_evaluator import (
    SDEvaluatorOutput,
    SUBMIT_TOOL,
    SYSTEM_PROMPT,
    _build_user_message,
    evaluate,
)


# --- SDEvaluatorOutput shape ------------------------------------------------

def test_sd_evaluator_output_minimal():
    out = SDEvaluatorOutput(phase="clarify", suggested_move="nudge")
    assert out.phase == "clarify"
    assert out.checklist_covered == []
    assert out.checklist_missing_required == []
    assert out.pushback_triggered is None
    assert out.suggested_move == "nudge"


def test_sd_evaluator_output_full_payload():
    out = SDEvaluatorOutput(
        phase="high_level",
        checklist_covered=[3, 7, 9],
        checklist_missing_required=[5],
        pushback_triggered="no_capacity_estimate",
        suggested_move="pushback",
    )
    assert out.checklist_covered == [3, 7, 9]
    assert out.checklist_missing_required == [5]
    assert out.pushback_triggered == "no_capacity_estimate"


def test_sd_evaluator_output_rejects_invalid_phase():
    with pytest.raises(ValidationError):
        SDEvaluatorOutput(phase="not_a_phase", suggested_move="nudge")


def test_sd_evaluator_output_rejects_invalid_move():
    with pytest.raises(ValidationError):
        SDEvaluatorOutput(phase="clarify", suggested_move="invent_a_move")


def test_sd_evaluator_output_accepts_all_five_moves():
    for move in ("press_on_missing", "advance_phase", "pushback", "nudge", "reanchor"):
        SDEvaluatorOutput(phase="clarify", suggested_move=move)  # must not raise


# --- _build_user_message rendering ------------------------------------------

def test_build_user_message_includes_all_blocks():
    statement = "Design a URL shortener."
    phases = [
        {"phase": "clarify", "ordinal": 1, "checklist": [
            {"id": 11, "item": "scope", "required": True}]},
        {"phase": "estimate", "ordinal": 2, "checklist": [
            {"id": 21, "item": "QPS", "required": True}]},
    ]
    pushbacks = [
        {"trigger_tag": "no_qps", "trigger_desc": "skipped capacity",
         "response": "How many QPS?"},
    ]
    history = [
        {"phase": "clarify", "user_text": "I'd start by asking who the users are."},
    ]
    user_text = "Let's say 100M URLs/year."

    msg = _build_user_message(
        question_statement=statement,
        phases=phases,
        pushbacks=pushbacks,
        session_so_far=history,
        user_text=user_text,
    )
    assert "Design a URL shortener" in msg
    assert "clarify" in msg and "estimate" in msg
    assert "QPS" in msg
    assert "no_qps" in msg
    assert "100M URLs/year" in msg
    # History section appears.
    assert "I'd start by asking" in msg
    # Section ordering: phases before pushbacks before session_so_far before
    # candidate_message. A bug that swapped XML tags would still satisfy the
    # substring asserts above but fail this one.
    assert (msg.index("<phases>")
            < msg.index("<pushbacks>")
            < msg.index("<session_so_far>")
            < msg.index("<candidate_message>"))


def test_build_user_message_handles_empty_history():
    msg = _build_user_message(
        question_statement="x" * 50,
        phases=[{"phase": "clarify", "ordinal": 1, "checklist": [
            {"id": 1, "item": "a", "required": True}]}],
        pushbacks=[{"trigger_tag": "t", "trigger_desc": "d", "response": "r"}],
        session_so_far=[],
        user_text="first turn",
    )
    assert "first turn" in msg


# --- SUBMIT_TOOL shape -----------------------------------------------------

def test_submit_tool_has_required_keys():
    assert SUBMIT_TOOL["name"] == "submit_sd_evaluation"
    assert "description" in SUBMIT_TOOL
    schema = SUBMIT_TOOL["input_schema"]
    # Pydantic-generated JSON schema must include the required fields.
    assert "phase" in schema["properties"]
    assert "suggested_move" in schema["properties"]


def test_system_prompt_mentions_sd_concepts():
    """Sanity: the SD prompt should mention phases and pushbacks. If someone
    accidentally points it at the algo prompt, this catches it."""
    assert "phase" in SYSTEM_PROMPT.lower()
    assert "pushback" in SYSTEM_PROMPT.lower()
    assert "submit_sd_evaluation" in SYSTEM_PROMPT


# --- evaluate() with mocked Anthropic --------------------------------------

def _mock_response_with_tool_use(payload: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_sd_evaluation"
    block.input = payload
    response = MagicMock()
    response.content = [block]
    return response


def test_evaluate_returns_parsed_output():
    client = MagicMock()
    client.messages.create.return_value = _mock_response_with_tool_use({
        "phase": "estimate",
        "checklist_covered": [2],
        "checklist_missing_required": [],
        "pushback_triggered": None,
        "suggested_move": "advance_phase",
    })
    out = evaluate(
        client=client,
        question_statement="x" * 50,
        phases=[{"phase": "clarify", "ordinal": 1,
                 "checklist": [{"id": 1, "item": "a", "required": True}]}],
        pushbacks=[{"trigger_tag": "t", "trigger_desc": "d" * 25, "response": "r" * 25}],
        session_so_far=[],
        user_text="100M users",
    )
    assert isinstance(out, SDEvaluatorOutput)
    assert out.phase == "estimate"
    assert out.suggested_move == "advance_phase"


def test_evaluate_raises_value_error_when_no_tool_use():
    client = MagicMock()
    response = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    response.content = [text_block]
    client.messages.create.return_value = response
    with pytest.raises(ValueError, match="no tool_use"):
        evaluate(
            client=client,
            question_statement="x" * 50,
            phases=[{"phase": "clarify", "ordinal": 1,
                     "checklist": [{"id": 1, "item": "a", "required": True}]}],
            pushbacks=[{"trigger_tag": "t", "trigger_desc": "d" * 25, "response": "r" * 25}],
            session_so_far=[],
            user_text="x",
        )


def test_evaluate_uses_forced_tool_choice():
    """Sanity: the call must specify tool_choice forcing submit_sd_evaluation,
    otherwise the model can return free text and we get ValueError every time."""
    client = MagicMock()
    client.messages.create.return_value = _mock_response_with_tool_use({
        "phase": "clarify",
        "checklist_covered": [],
        "checklist_missing_required": [1],
        "pushback_triggered": None,
        "suggested_move": "press_on_missing",
    })
    evaluate(
        client=client,
        question_statement="x" * 50,
        phases=[{"phase": "clarify", "ordinal": 1,
                 "checklist": [{"id": 1, "item": "a", "required": True}]}],
        pushbacks=[{"trigger_tag": "t", "trigger_desc": "d" * 25, "response": "r" * 25}],
        session_so_far=[],
        user_text="x",
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["tool_choice"] == {"type": "tool", "name": "submit_sd_evaluation"}
    # System prompt is the SD one, not the algo one (defensive: catches wiring mistakes).
    assert "phase" in kwargs["system"].lower()


# --- typing contract: client=None on agent_sdk backend ---------------------

def test_evaluate_accepts_none_client_on_agent_sdk_backend(monkeypatch):
    """The agent_sdk backend ignores `client` (it constructs its own SDK MCP
    server). The public signature must permit None to match runtime behavior
    in eval/run_sd_eval.py, which passes client=None on that backend.

    Also pin pass-through: a future defensive default inside `evaluate()`
    (e.g. `client = client or get_anthropic_client()`) would silently break
    the agent_sdk caller's intent - building a client triggers
    ANTHROPIC_API_KEY errors on that backend. Capturing the inner-call kwargs
    catches that regression."""
    monkeypatch.setenv("CHAT_BACKEND", "agent_sdk")
    from whiteboard_mcp import sd_evaluator as mod

    fixture = SDEvaluatorOutput(phase="clarify", suggested_move="nudge")
    captured: dict = {}

    def _fake_backend(**kw):
        captured.update(kw)
        return fixture

    monkeypatch.setattr(mod, "evaluate_with_forced_tool", _fake_backend)

    out = evaluate(
        client=None,
        question_statement="x" * 50,
        phases=[{"phase": "clarify", "ordinal": 1,
                 "checklist": [{"id": 1, "item": "a", "required": True}]}],
        pushbacks=[{"trigger_tag": "t", "trigger_desc": "d" * 25, "response": "r" * 25}],
        session_so_far=[],
        user_text="hi",
    )
    assert out is fixture
    assert captured["client"] is None
