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
import asyncio
import os
from typing import Any, TypeVar

from claude_agent_sdk import (
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    query,
    tool,
)
from pydantic import BaseModel

from whiteboard_mcp._anthropic import get_anthropic_client


T = TypeVar("T", bound=BaseModel)

# 60s upper bound on the inner LLM call. Honored on BOTH backends:
# - api path: passed as `timeout=` to client.messages.create.
# - agent_sdk path: asyncio.wait_for around _run_query_capture_emit;
#   timeout fires per attempt (so the retry can still run within budget
#   if the first attempt times out).
EVALUATOR_TIMEOUT_S = 60.0


def evaluate_with_forced_tool(
    *,
    system: str,
    user_text: str,
    output_schema: type[T],
    tool_name: str,
    model: str,
    client: Any | None,
) -> T:
    """Single entry point. Raises:
    - ValueError if the model returned no tool_use block (api path) or
      no emit call after retry (agent_sdk path)
    - pydantic.ValidationError on malformed payloads
    - anthropic.APITimeoutError on api-path timeout
    - asyncio.TimeoutError on agent_sdk-path timeout

    `client` is honored only on the metered (api) path. Pass `None` on
    the agent_sdk path - it constructs its own SDK MCP server and
    ignores this argument. The kwarg has no default to make every
    caller think about which backend they're targeting.
    """
    backend = os.environ.get("CHAT_BACKEND", "api")
    if backend not in ("api", "agent_sdk"):
        raise ValueError(
            f"CHAT_BACKEND must be 'api' or 'agent_sdk', got {backend!r}"
        )
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


async def _run_query_capture_emit(
    system: str, user_text: str, output_schema: type[T],
    tool_name: str, model: str, is_retry: bool,
) -> dict | None:
    """Run one Agent SDK query() with an in-process emit tool registered.
    Returns the captured tool_input dict, or None if the model didn't
    call emit (the caller decides whether to retry or raise).

    The schema's properties are exposed via the tool's input_schema so
    the model knows the expected shape. This is best-effort enforcement
    (no tool_choice equivalent in Agent SDK) - the system prompt's
    directive that the model MUST call the tool is the load-bearing
    piece. `is_retry=True` appends a sterner suffix on the second
    attempt."""
    captured: dict | None = None

    @tool(
        tool_name,
        f"Emit a structured {output_schema.__name__} payload.",
        output_schema.model_json_schema(),
    )
    async def emit(payload: dict) -> dict:
        nonlocal captured
        captured = payload
        return payload

    server = create_sdk_mcp_server(name="ev", tools=[emit])
    retry_suffix = (
        "\n\nYour previous response did not call the emit tool. Call it now."
        if is_retry else ""
    )
    base_directive = (
        f"\n\nYou MUST call the {tool_name} tool with your structured output. "
        f"Do not write prose."
    )
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system + base_directive + retry_suffix,
        mcp_servers={"ev": server},
        # tools=[] disables all built-in Claude Code tools (Bash, Read,
        # ToolSearch, etc.). Without it, the SDK ships those by default
        # and the model uses them instead of staying focused on calling
        # our emit tool.
        tools=[],
        allowed_tools=[f"mcp__ev__{tool_name}"],
        permission_mode="bypassPermissions",
    )
    async for _msg in query(prompt=user_text, options=options):
        # The @tool decorator captures the input via the closure above;
        # we don't need to inspect msg here. Iteration drains the
        # generator so the SDK can clean up its subprocess.
        pass
    return captured


def _evaluate_agent_sdk(
    system: str, user_text: str, output_schema: type[T],
    tool_name: str, model: str,
) -> T:
    # Per-attempt timeout: each call to the SDK gets the full budget,
    # so the retry can run even if the first attempt times out.
    # asyncio.TimeoutError surfaces to the MCP error path same way
    # APITimeoutError does on the metered backend.
    captured = asyncio.run(
        asyncio.wait_for(
            _run_query_capture_emit(
                system, user_text, output_schema, tool_name, model, is_retry=False,
            ),
            timeout=EVALUATOR_TIMEOUT_S,
        )
    )
    if captured is None:
        captured = asyncio.run(
            asyncio.wait_for(
                _run_query_capture_emit(
                    system, user_text, output_schema, tool_name, model, is_retry=True,
                ),
                timeout=EVALUATOR_TIMEOUT_S,
            )
        )
    if captured is None:
        raise ValueError(f"evaluator did not call emit (tool_name={tool_name})")
    return output_schema.model_validate(captured)
