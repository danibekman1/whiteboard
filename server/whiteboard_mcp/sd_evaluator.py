"""Inner Opus evaluator for system-design sessions.

Parallel to whiteboard_mcp/evaluator.py: same forced-tool-use pattern, same
exception contract. Different schema (SDEvaluatorOutput) and different
input shape (phases + pushbacks + session history instead of canonical
linear steps).

Per design doc Section 4: the evaluator decides which phase the candidate
is in and what move the outer coach should make next; the outer coach
owns when to advance phases (asks user permission)."""
from __future__ import annotations
import os
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from whiteboard_mcp._evaluator_backend import EVALUATOR_TIMEOUT_S, evaluate_with_forced_tool


Phase = Literal["clarify", "estimate", "high_level", "deep_dive", "tradeoffs"]
SDMove = Literal["press_on_missing", "advance_phase", "pushback", "nudge", "reanchor"]

# Used by evaluate_sd_attempt._load_session_so_far when a prior attempt's
# evaluator_json is malformed. Living next to the Phase Literal so the two
# move together if the phase set ever shifts.
DEFAULT_PHASE_FALLBACK: Phase = "clarify"


class SDEvaluatorOutput(BaseModel):
    phase: Phase = Field(
        description="Which phase the candidate is currently working in."
    )
    # default_factory=list mirrors EvaluatorOutput.missing - the model
    # legitimately omits these when there's nothing to report, and we want
    # [] not a validation error.
    checklist_covered: list[int] = Field(
        default_factory=list,
        description=(
            "Checklist item ids in the current phase that the candidate has "
            "addressed across this turn AND prior turns (cumulative). Use the "
            "ids from the phases input."
        ),
    )
    checklist_missing_required: list[int] = Field(
        default_factory=list,
        description=(
            "Required checklist item ids in the current phase that the "
            "candidate has NOT yet addressed."
        ),
    )
    pushback_triggered: str | None = Field(
        default=None,
        description=(
            "trigger_tag of a pushback that should fire this turn, or null "
            "if none. Pull the value from the pushbacks input verbatim."
        ),
    )
    suggested_move: SDMove = Field(
        description=(
            "press_on_missing: surface ONE missing required item. "
            "advance_phase: candidate covered required items; coach should ask "
            "permission to move to next phase. "
            "pushback: deliver the pushback identified by pushback_triggered. "
            "nudge: candidate is on track but vague; ask for a number or specific. "
            "reanchor: candidate went off-topic; redirect to current phase."
        )
    )


SYSTEM_PROMPT = """You are a system-design interview coach's structured evaluator.

You will receive:
- The interview question statement.
- The five phases (clarify, estimate, high_level, deep_dive, tradeoffs)
  with each phase's checklist of items the candidate should address.
- The set of pushbacks for this question (adversarial moves keyed by
  trigger conditions).
- The candidate's session-so-far (previous attempts and which phase they
  resolved to).
- The candidate's latest message.

Your job per turn:
1. Decide which phase the candidate is currently in. If ambiguous between
   two phases, stay in the earlier phase (do not auto-advance).
2. Identify which checklist items in the current phase the candidate has
   covered (across this turn and prior turns) and which required items
   are still missing.
3. Decide whether a pushback should fire this turn (return its trigger_tag
   verbatim), or null if none applies.
4. Pick a suggested_move to direct the outer coach.

Submit your assessment by calling the submit_sd_evaluation tool. Do not
respond in plain text.

Suggested moves:
- press_on_missing: candidate is in the right phase but a required item is
  uncovered. Outer coach should surface ONE missing item as a question.
- advance_phase: candidate has covered required items in current phase.
  Outer coach should summarize and ASK permission before moving on.
- pushback: a pushback trigger fires; outer coach delivers the matching
  response adversarially.
- nudge: candidate is on the right track but vague; outer coach should ask
  for a number, a specific component, or a concrete example.
- reanchor: candidate is off-topic or wrote nonsense; outer coach should
  redirect to the current phase.
"""


SUBMIT_TOOL = {
    "name": "submit_sd_evaluation",
    "description": "Submit the structured evaluation of the candidate's latest message for an SD session.",
    "input_schema": SDEvaluatorOutput.model_json_schema(),
}


def _build_user_message(
    question_statement: str,
    phases: list[dict],
    pushbacks: list[dict],
    session_so_far: list[dict],
    user_text: str,
) -> str:
    phases_lines = []
    for ph in phases:
        phases_lines.append(f"  Phase {ph['ordinal']}. {ph['phase']}")
        for item in ph["checklist"]:
            req = "*" if item.get("required", True) else " "
            phases_lines.append(f"    [{req}] (id={item['id']}) {item['item']}")
    phases_block = "\n".join(phases_lines)

    pb_lines = []
    for pb in pushbacks:
        pb_lines.append(
            f"  - trigger={pb['trigger_tag']}: {pb['trigger_desc']}\n"
            f"    response: {pb['response']}"
        )
    pushbacks_block = "\n".join(pb_lines)

    history_lines = []
    for h in session_so_far:
        history_lines.append(
            f"  [phase={h['phase']}] {h['user_text']}"
        )
    history_block = "\n".join(history_lines) if history_lines else "  (no prior turns)"

    return (
        f"<question>\n{question_statement}\n</question>\n\n"
        f"<phases>\n{phases_block}\n</phases>\n\n"
        f"<pushbacks>\n{pushbacks_block}\n</pushbacks>\n\n"
        f"<session_so_far>\n{history_block}\n</session_so_far>\n\n"
        f"<candidate_message>\n{user_text}\n</candidate_message>"
    )


def evaluate(
    *,
    client: anthropic.Anthropic,
    question_statement: str,
    phases: list[dict],
    pushbacks: list[dict],
    session_so_far: list[dict],
    user_text: str,
    model: str | None = None,
) -> SDEvaluatorOutput:
    """Run the inner SD evaluator. Raises ValueError if the model returned no
    tool_use block; raises pydantic.ValidationError on malformed payloads;
    raises anthropic.APITimeoutError if the call exceeds EVALUATOR_TIMEOUT_S.
    The caller is responsible for translating these to MCP error dicts.

    `client` is honored on the metered (api) backend; ignored on the
    agent_sdk backend, which constructs its own SDK MCP server."""
    model = model or os.environ.get("CLAUDE_COACH_MODEL", "claude-opus-4-7")
    return evaluate_with_forced_tool(
        system=SYSTEM_PROMPT,
        user_text=_build_user_message(
            question_statement=question_statement,
            phases=phases,
            pushbacks=pushbacks,
            session_so_far=session_so_far,
            user_text=user_text,
        ),
        output_schema=SDEvaluatorOutput,
        tool_name="submit_sd_evaluation",
        model=model,
        client=client,
    )
