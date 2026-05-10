"""Tests for the evaluator backend factory.

The metered path is exercised by the existing evaluate_attempt /
evaluate_sd_attempt tool tests. These tests focus on the agent_sdk path,
which is mocked rather than hitting Claude Code's CLI subprocess.
"""
from __future__ import annotations
import asyncio
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
            tool_name="emit", model="claude-haiku-4-5", client=None,
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
            tool_name="emit", model="claude-haiku-4-5", client=None,
        )
    assert mock.await_count == 2
    # Second attempt must use is_retry=True so the sterner suffix fires.
    assert mock.await_args_list[0].kwargs.get("is_retry") is False or \
           mock.await_args_list[0].args[-1] is False
    assert mock.await_args_list[1].kwargs.get("is_retry") is True or \
           mock.await_args_list[1].args[-1] is True
    assert out.n == 1


def test_agent_sdk_raises_after_two_missing_emits(env_agent_sdk):
    mock = AsyncMock(return_value=None)
    with patch.object(_evaluator_backend, "_run_query_capture_emit", new=mock):
        with pytest.raises(ValueError, match="did not call emit"):
            _evaluator_backend.evaluate_with_forced_tool(
                system="S", user_text="U", output_schema=_DummyOutput,
                tool_name="emit", model="claude-haiku-4-5", client=None,
            )
    assert mock.await_count == 2


def test_metered_path_runs_when_backend_unset(monkeypatch):
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    fake_client = MagicMock()
    block = MagicMock(type="tool_use", input={"foo": "ok", "n": 2})
    # MagicMock auto-creates `name` as another MagicMock, so set it explicitly.
    block.name = "emit"
    fake_client.messages.create.return_value.content = [block]
    out = _evaluator_backend.evaluate_with_forced_tool(
        system="S", user_text="U", output_schema=_DummyOutput,
        tool_name="emit", model="claude-opus-4-7", client=fake_client,
    )
    assert out.n == 2
    fake_client.messages.create.assert_called_once()


def test_invalid_backend_value_raises(monkeypatch):
    monkeypatch.setenv("CHAT_BACKEND", "apl")  # typo of "api"
    with pytest.raises(ValueError, match="CHAT_BACKEND must be"):
        _evaluator_backend.evaluate_with_forced_tool(
            system="S", user_text="U", output_schema=_DummyOutput,
            tool_name="emit", model="claude-opus-4-7", client=None,
        )


# --- _run_query_capture_emit options shape ---------------------------------
# Monkey-patch the SDK's query() to capture the ClaudeAgentOptions the
# evaluator built and assert the load-bearing fields. Without this, a
# regression that drops `tools=[]` or the "MUST call" directive on the
# SDK path is undetectable.

def _drain_then_return(fn):
    """Wrap a coroutine so we can pull out the recorded args after a
    one-shot async generator drain."""
    captured: dict = {}

    async def gen(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        # Empty stream; emit was never called -> _run_query_capture_emit
        # returns None.
        return
        yield  # unreachable; makes this an async generator
    return gen, captured


def test_run_query_capture_emit_builds_correct_options(env_agent_sdk):
    """Assert the SDK is invoked with: system_prompt containing the MUST
    directive, mcp_servers={'ev': <server>}, tools=[] (no built-ins),
    allowed_tools=['mcp__ev__<tool>'], permission_mode='bypassPermissions'.
    """
    captured: dict = {}

    async def fake_query(*, prompt, options, **_):
        captured["prompt"] = prompt
        captured["options"] = options
        if False:
            yield  # keep async-generator type

    with patch.object(_evaluator_backend, "query", new=fake_query):
        result = asyncio.run(
            _evaluator_backend._run_query_capture_emit(
                system="S", user_text="U", output_schema=_DummyOutput,
                tool_name="emit", model="claude-haiku-4-5", is_retry=False,
            )
        )
    assert result is None  # fake_query yields nothing -> emit never called
    opts = captured["options"]
    assert opts.model == "claude-haiku-4-5"
    assert opts.tools == []  # built-ins disabled
    assert opts.allowed_tools == ["mcp__ev__emit"]
    assert opts.permission_mode == "bypassPermissions"
    assert "MUST call the emit tool" in opts.system_prompt
    assert "Your previous response did not call" not in opts.system_prompt  # no retry suffix
    assert "ev" in opts.mcp_servers
    assert captured["prompt"] == "U"


def test_run_query_capture_emit_retry_appends_sterner_suffix(env_agent_sdk):
    """is_retry=True must add the sterner suffix to the system prompt."""
    captured: dict = {}

    async def fake_query(*, prompt, options, **_):
        captured["options"] = options
        if False:
            yield

    with patch.object(_evaluator_backend, "query", new=fake_query):
        asyncio.run(
            _evaluator_backend._run_query_capture_emit(
                system="S", user_text="U", output_schema=_DummyOutput,
                tool_name="emit", model="claude-haiku-4-5", is_retry=True,
            )
        )
    assert "Your previous response did not call the emit tool" in captured["options"].system_prompt
