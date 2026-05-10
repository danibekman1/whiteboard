"""Tests for the evaluator backend factory.

The metered path is exercised by the existing evaluate_attempt /
evaluate_sd_attempt tool tests. These tests focus on the agent_sdk path,
which is mocked rather than hitting Claude Code's CLI subprocess.
"""
from __future__ import annotations
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from pydantic import BaseModel

from whiteboard_mcp import _evaluator_backend


class _DummyOutput(BaseModel):
    foo: str
    n: int


@pytest.fixture
def env_agent_sdk(monkeypatch):
    monkeypatch.setenv("CHAT_BACKEND", "agent_sdk")
    yield


def test_agent_sdk_returns_pydantic_from_emit_call(env_agent_sdk):
    with patch.object(
        _evaluator_backend, "_run_query_capture_emit",
        new=AsyncMock(return_value={"foo": "x", "n": 7}),
    ):
        out = _evaluator_backend.evaluate_with_forced_tool(
            system="S", user_text="U", output_schema=_DummyOutput,
            tool_name="emit", model="claude-haiku-4-5",
        )
    assert isinstance(out, _DummyOutput)
    assert out.foo == "x" and out.n == 7


def test_agent_sdk_retries_once_on_missing_emit(env_agent_sdk):
    # First call returns None (no emit), second call returns valid payload.
    side_effects = [None, {"foo": "ok", "n": 1}]
    mock = AsyncMock(side_effect=side_effects)
    with patch.object(_evaluator_backend, "_run_query_capture_emit", new=mock):
        out = _evaluator_backend.evaluate_with_forced_tool(
            system="S", user_text="U", output_schema=_DummyOutput,
            tool_name="emit", model="claude-haiku-4-5",
        )
    assert mock.await_count == 2
    assert out.n == 1


def test_agent_sdk_raises_after_two_missing_emits(env_agent_sdk):
    mock = AsyncMock(return_value=None)
    with patch.object(_evaluator_backend, "_run_query_capture_emit", new=mock):
        with pytest.raises(ValueError, match="did not call emit"):
            _evaluator_backend.evaluate_with_forced_tool(
                system="S", user_text="U", output_schema=_DummyOutput,
                tool_name="emit", model="claude-haiku-4-5",
            )
    assert mock.await_count == 2


def test_metered_path_runs_when_backend_unset(monkeypatch):
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    fake_client = MagicMock()
    fake_client.messages.create.return_value.content = [
        MagicMock(type="tool_use", name="emit", input={"foo": "ok", "n": 2}),
    ]
    # Mock the inner tool_use block: MagicMock auto-creates `name` as another
    # MagicMock, so set it explicitly.
    fake_client.messages.create.return_value.content[0].name = "emit"
    with patch.object(_evaluator_backend, "get_anthropic_client", return_value=fake_client):
        out = _evaluator_backend.evaluate_with_forced_tool(
            system="S", user_text="U", output_schema=_DummyOutput,
            tool_name="emit", model="claude-opus-4-7",
        )
    assert out.n == 2
    fake_client.messages.create.assert_called_once()
