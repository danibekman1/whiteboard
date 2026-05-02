"""Generate one question's full JSON from a seed entry, via Opus forced tool-use."""
from __future__ import annotations
import os
from dataclasses import dataclass

import anthropic

from bank.schemas import QuestionJSON


@dataclass
class GenerationInput:
    slug: str
    title: str
    difficulty: str
    topic: str  # primary topic slug (additional topics OK in output)
    leetcode_id: int | None = None
    optimal_time: str | None = None
    optimal_space: str | None = None


SYSTEM_PROMPT = """You are an expert software-engineering interview question author.

You will receive a brief description of a known interview problem (slug,
title, difficulty, primary topic, optimal complexity). Produce a complete
question record by calling submit_question.

Requirements:

- statement: clear, concise, LeetCode-style. Include I/O constraints, but
  avoid pasting LeetCode's exact wording.
- canonical_solution.code: pure Python 3 function, named after the slug
  with hyphens replaced by underscores (slug 'two-sum' -> 'two_sum').
  No imports unless strictly required. No I/O. Function takes positional
  args matching test_cases input lists.
  For linked-list problems, use the class name `ListNode` directly
  (already defined in the runner with attributes `val` and `next`).
  For binary-tree problems, use `TreeNode` (with `val`, `left`, `right`).
  Do NOT redefine these classes in your code.
- canonical_solution.time/space: must match the optimal complexity given
  in the seed (notation like 'O(n)', 'O(n log n)', 'O(1)').
- topics: list of kebab-case topic slugs. The FIRST entry MUST be the
  exact 'primary topic' slug given in the seed, copied verbatim
  (e.g. seed says 'arrays-hashing' -> first topic is 'arrays-hashing',
  not 'arrays' or 'hashing' or 'hash-map'). You may add additional
  related topics after, but keep the seed's slug first.
- test_cases: minimum 3, must include at least one edge case (empty,
  single element, duplicate values, target=0, etc.). Inputs are positional
  args to the function.

  For linked lists, encode each list as
      {"__linked_list__": [v1, v2, v3]}
  meaning a chain v1->v2->v3. The empty list {"__linked_list__": []}
  decodes to None (an empty head). Use this for both inputs and expecteds
  whenever a ListNode is involved.

  For binary trees, encode using LeetCode's BFS array notation:
      {"__tree__": [1, 2, 3, null, 4]}
  i.e. level-order with `null` for absent children. {"__tree__": []}
  decodes to None. Use this for both inputs and expecteds whenever a
  TreeNode is involved.

  These markers are decoded into real ListNode/TreeNode instances before
  your function is called, and the returned value is structurally
  compared against the decoded expected. So your function should accept
  and return the natural Node types, not the encoded dicts.
- steps: 3-10 steps capturing the SOCRATIC reasoning a candidate should
  articulate at the whiteboard. Each step is a *thought* the candidate
  has, in order. NOT code. Pattern tags are short lowercase identifiers
  like 'complexity-analysis', 'hashing', 'edge-cases'.
- hints: exactly 3 per step, escalating from gentle (level 1) to revealing
  (level 3). Level 3 should make the step almost impossible to miss.

Submit by calling submit_question. Do not respond in plain text.
"""


def _build_user_message(seed: GenerationInput) -> str:
    parts = [
        f"slug: {seed.slug}",
        f"title: {seed.title}",
        f"difficulty: {seed.difficulty}",
        f"primary topic: {seed.topic}",
    ]
    if seed.leetcode_id is not None:
        parts.append(f"leetcode_id: {seed.leetcode_id}")
    if seed.optimal_time:
        parts.append(f"optimal time: {seed.optimal_time}")
    if seed.optimal_space:
        parts.append(f"optimal space: {seed.optimal_space}")
    return "\n".join(parts)


SUBMIT_TOOL = {
    "name": "submit_question",
    "description": "Submit the complete question record.",
    "input_schema": QuestionJSON.model_json_schema(),
}


def generate(
    *,
    client: anthropic.Anthropic,
    seed: GenerationInput,
    model: str | None = None,
    extra_user_note: str | None = None,
) -> QuestionJSON:
    """One-shot generation. extra_user_note is appended on retry."""
    model = model or os.environ.get("CLAUDE_COACH_MODEL", "claude-opus-4-7")
    user = _build_user_message(seed)
    if extra_user_note:
        user += f"\n\nNote on this attempt:\n{extra_user_note}"
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        tools=[SUBMIT_TOOL],
        tool_choice={"type": "tool", "name": "submit_question"},
        messages=[{"role": "user", "content": user}],
        timeout=120.0,
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_question":
            return QuestionJSON.model_validate(block.input)
    raise ValueError("generator returned no tool_use block")


class GenerationFailed(Exception):
    def __init__(self, slug: str, attempt_errors: list[str]):
        self.slug = slug
        self.attempt_errors = attempt_errors
        super().__init__(f"{slug}: {len(attempt_errors)} attempts failed: {attempt_errors[-1]}")


def generate_with_retries(
    *,
    client: anthropic.Anthropic,
    seed: GenerationInput,
    max_attempts: int = 3,
    model: str | None = None,
) -> QuestionJSON:
    errors: list[str] = []
    note: str | None = None
    for attempt in range(max_attempts):
        try:
            return generate(client=client, seed=seed, model=model, extra_user_note=note)
        except Exception as e:
            errors.append(f"attempt {attempt + 1}: {e}")
            note = (
                "Previous attempt failed validation:\n"
                f"{e}\n\n"
                "Address the specific failure above and resubmit."
            )
    raise GenerationFailed(slug=seed.slug, attempt_errors=errors)
