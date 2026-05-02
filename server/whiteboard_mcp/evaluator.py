"""Inner Opus evaluator. The new piece vs shapes.

Uses Anthropic's forced tool-use pattern for structured output: declare a
single tool 'submit_evaluation' with the EvaluatorOutput schema as
input_schema, force the model to call it, then parse the tool input.
"""
from __future__ import annotations
import os
from typing import Literal

import anthropic
from pydantic import BaseModel, Field


class EvaluatorOutput(BaseModel):
    step_id: int = Field(description="Ordinal of the step the user is currently working on.")
    correct: bool = Field(description="Did the user nail this step?")
    missing: list[str] = Field(default_factory=list, description="What's missing if not correct.")
    suggested_move: Literal["nudge", "advance", "reanchor", "wrap_up"]


SYSTEM_PROMPT = """You are an interview coach's structured evaluator.

You will receive:
- The interview question statement.
- The canonical sequence of reasoning steps the candidate should articulate.
- The candidate's latest message.

Your job: classify which step the candidate is currently working on, whether
they nailed it, what's missing if not, and what move the outer coach should
make next.

Submit your assessment by calling the submit_evaluation tool. Do not respond
in plain text.

Suggested moves:
- nudge: candidate is on the right step but missing something. Push them.
- advance: current step is complete. Outer coach should prompt the next step.
- reanchor: candidate went off-topic or wrote nonsense. Redirect gently.
- wrap_up: all steps cleared. Time to summarize and end.
"""


SUBMIT_TOOL = {
    "name": "submit_evaluation",
    "description": "Submit the structured evaluation of the candidate's latest message.",
    "input_schema": EvaluatorOutput.model_json_schema(),
}


def _build_user_message(
    question_statement: str,
    canonical_steps: list[dict],
    user_text: str,
) -> str:
    steps_block = "\n".join(
        f"  {s['ordinal']}. {s['description']}" for s in canonical_steps
    )
    return (
        f"<question>\n{question_statement}\n</question>\n\n"
        f"<canonical_steps>\n{steps_block}\n</canonical_steps>\n\n"
        f"<candidate_message>\n{user_text}\n</candidate_message>"
    )


def get_anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def evaluate(
    *,
    client: anthropic.Anthropic,
    question_statement: str,
    canonical_steps: list[dict],
    user_text: str,
    model: str | None = None,
) -> EvaluatorOutput:
    """Run the inner evaluator. Raises ValueError if the model returned no
    tool_use block; raises pydantic.ValidationError on malformed payloads.
    The caller is responsible for translating these to MCP error dicts."""
    model = model or os.environ.get("CLAUDE_COACH_MODEL", "claude-opus-4-7")
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[SUBMIT_TOOL],
        tool_choice={"type": "tool", "name": "submit_evaluation"},
        messages=[{
            "role": "user",
            "content": _build_user_message(question_statement, canonical_steps, user_text),
        }],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_evaluation":
            return EvaluatorOutput.model_validate(block.input)
    raise ValueError("evaluator returned no tool_use block")
