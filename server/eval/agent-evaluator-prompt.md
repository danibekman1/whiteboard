# Pedagogy eval — sub-agent prompt template (dev fallback)

> **Use this when**: developer wants to sanity-check the pedagogy eval cases but
> doesn't have Anthropic API credits handy. The orchestrating Claude Code
> session reads `eval/cases.yaml`, dispatches one sub-agent per case using this
> template, and aggregates PASS/FAIL.
>
> **Production eval (`eval.run_eval` via Anthropic SDK + `whiteboard_mcp/
> evaluator.py`'s forced-tool-use `submit_evaluation` prompt) is unchanged and
> remains the gold-standard signal**. The sub-agent path uses free-form JSON
> output and whatever model Claude Code is configured with (not necessarily
> `claude-opus-4-7`), so it is a useful proxy for case-shape sanity but does
> NOT validate the production evaluator's tool-use plumbing.

---

## Per-case prompt (substitute the bracketed slots)

You are a structured evaluator for a Socratic interview coach.

You will receive a question slug and the candidate's latest message. Look up
the question's canonical reasoning steps from the bank, then classify the
candidate.

### Inputs

- Question slug: `[SLUG]`
- Candidate's latest message (user_text):

```
[USER_TEXT]
```

### Lookup

Read `/home/frtlx/whiteboard/server/bank/generated/[SLUG].json` (Read tool).
- Use `d["statement"]` as the question statement.
- Use `d["steps"][i]["description"]` (in order) as the canonical reasoning
  steps. Each step's `ordinal` is the 1-based position.

### Classification

Decide:

- `step_ordinal` (int): 1-based ordinal of the step the candidate is currently
  working on. If their message clearly addresses step N, that's N.
- `correct` (bool): did they nail this step (the key insight is articulated
  clearly)? If they're on the right step but missing something, `false`.
- `missing` (list[str]): empty if `correct=true`. Otherwise, short
  bullet-style strings describing what's missing.
- `suggested_move` (str): one of:
  - `"nudge"` — candidate is on the right step but missing something. Push them.
  - `"advance"` — current step is complete; prompt the next step.
  - `"reanchor"` — candidate went off-topic / wrote nonsense; redirect.
  - `"wrap_up"` — all steps cleared; summarize and end.

### Output

Reply with **EXACTLY one JSON line and nothing else** (no prose, no markdown
fences, no explanation). Example shape:

```
{"step_ordinal": 3, "correct": true, "missing": [], "suggested_move": "advance"}
```

The orchestrator parses your line as JSON and compares against expected
fields case by case.
