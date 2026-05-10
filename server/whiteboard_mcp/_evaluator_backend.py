"""Evaluator backend factory.

Both evaluators (algo and SD) call evaluate_with_forced_tool to coerce
their inner LLM call into a Pydantic schema. This module dispatches on
CHAT_BACKEND env:

- 'api'        -> Anthropic Messages API with tool_choice (today's path)
- 'agent_sdk'  -> Claude Agent SDK with an in-process SDK MCP 'emit' tool

The api path is unconditionally available (uses ANTHROPIC_API_KEY). The
agent_sdk path requires CLAUDE_CODE_OAUTH_TOKEN.
"""
from __future__ import annotations
import os
from typing import Any, TypeVar

from pydantic import BaseModel

from whiteboard_mcp._anthropic import get_anthropic_client


T = TypeVar("T", bound=BaseModel)

EVALUATOR_TIMEOUT_S = 60.0


def evaluate_with_forced_tool(
    *,
    system: str,
    user_text: str,
    output_schema: type[T],
    tool_name: str,
    model: str,
    client: Any | None = None,
) -> T:
    """Single entry point. Raises:
    - ValueError if the model returned no tool_use block (api path) or no
      emit call (agent_sdk path)
    - pydantic.ValidationError on malformed payloads
    - anthropic.APITimeoutError on api-path timeout

    `client` is honored only on the metered (api) path. Tests that mock
    the Anthropic client pass it in here; the agent_sdk path constructs
    its own SDK MCP server and ignores this argument.
    """
    backend = os.environ.get("CHAT_BACKEND", "api")
    if backend == "agent_sdk":
        return _evaluate_agent_sdk(system, user_text, output_schema, tool_name, model)
    return _evaluate_metered(system, user_text, output_schema, tool_name, model, client)


def _evaluate_metered(
    system: str, user_text: str, output_schema: type[T], tool_name: str, model: str,
    client: Any | None,
) -> T:
    if client is None:
        client = get_anthropic_client()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        tools=[{
            "name": tool_name,
            "description": f"Emit a structured {output_schema.__name__} payload.",
            "input_schema": output_schema.model_json_schema(),
        }],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user_text}],
        timeout=EVALUATOR_TIMEOUT_S,
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return output_schema.model_validate(block.input)
    raise ValueError("evaluator returned no tool_use block")


def _evaluate_agent_sdk(
    _system: str, _user_text: str, _output_schema: type[T], _tool_name: str, _model: str,
) -> T:
    raise NotImplementedError("agent_sdk evaluator backend not yet implemented")
