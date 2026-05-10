# SD pedagogy eval — sub-agent prompt template (dev fallback)

> **Use this when**: developer wants to sanity-check the SD evaluator cases but
> doesn't have Anthropic API credits handy. The orchestrating Claude Code
> session reads `eval/sd_cases.yaml`, dispatches one sub-agent per case using
> this template, and aggregates PASS/FAIL.
>
> **Production eval (`eval.run_sd_eval` via Anthropic SDK + `whiteboard_mcp/
> sd_evaluator.py`'s forced-tool-use `submit_sd_evaluation` prompt) is unchanged
> and remains the gold-standard signal**. The sub-agent path uses free-form
> JSON output and whatever model Claude Code is configured with (not
> necessarily `claude-opus-4-7`), so it is a useful proxy for case-shape
> sanity but does NOT validate the production evaluator's tool-use plumbing.

---

## Per-case prompt (substitute the bracketed slots)

You are a structured evaluator for a system-design interview coach.

You will receive a question slug and the candidate's latest message. Look up
the question's curated phases, checklist, and pushbacks from the bank, then
classify the candidate.

### Inputs

- Question slug: `[SLUG]`
- Candidate's latest message (user_text):

```
[USER_TEXT]
```

### Lookup

Read `/home/frtlx/whiteboard/server/bank/seed/sd_curated/[SLUG].json` (Read tool).
- Use `d["statement"]` as the question statement.
- Use `d["phases"]` (in `ordinal` order) for the five phases (clarify, estimate,
  high_level, deep_dive, tradeoffs). Each phase has a `checklist` of items
  marked `required` true/false.
- Use `d["pushbacks"]` for the adversarial moves; each has a `trigger_tag`,
  `trigger_desc`, and `response`.

### Classification

Decide:

1. **`phase`** (string): which phase the candidate is currently working in.
   One of `clarify`, `estimate`, `high_level`, `deep_dive`, `tradeoffs`.
   If ambiguous between two phases, stay in the **earlier** one (do not
   auto-advance).
2. **`checklist_covered`** (list[int]): 1-based ordinals of checklist items
   in the current phase that the candidate has addressed across this turn.
   Use the order they appear in the JSON (no DB ids available in the
   sub-agent path).
3. **`checklist_missing_required`** (list[int]): required item ordinals in
   the current phase the candidate has NOT addressed.
4. **`pushback_triggered`** (string | null): `trigger_tag` of a pushback
   that should fire this turn (verbatim from the bank), or `null` if the
   candidate's message doesn't match any pushback's `trigger_desc`.
5. **`suggested_move`** (string): one of:
   - `press_on_missing` — candidate is in the right phase but a required item
     is uncovered. Coach surfaces ONE missing item.
   - `advance_phase` — candidate covered required items; coach asks
     permission to move on.
   - `pushback` — a pushback fires; coach delivers the matching response.
   - `nudge` — candidate is on track but vague; ask for a number or specific.
   - `reanchor` — candidate went off-topic; redirect to current phase.

### Output

Reply with **EXACTLY one JSON line and nothing else** (no prose, no markdown
fences, no explanation). Example shape:

```
{"phase": "estimate", "checklist_covered": [1,2], "checklist_missing_required": [3,4], "pushback_triggered": null, "suggested_move": "advance_phase"}
```

The orchestrator parses your line as JSON and compares against expected
fields case by case.

### Rules

- `pushback_triggered` is null unless the candidate's message specifically
  matches a pushback's `trigger_desc`.
- `suggested_move=advance_phase` only when required checklist items in the
  current phase are covered AND no pushback fires.

These rules mirror the production system prompt in
`whiteboard_mcp/sd_evaluator.py:SYSTEM_PROMPT`. If the production prompt
gains or loses a rule, update this file to keep the dev fallback a
faithful proxy of production. Don't add bespoke rules here that aren't
in production - that drifts the proxy and the sub-agent eval stops
predicting how the SDK path will behave.
