# Strict Review Decision Log - PR #3 (feat/v0.7-sd-eval-harness)

PR 6a of v0.7 finish plan: SD pedagogy eval harness.
First strict review on this branch. Verdict: Comment (no blockers).

User instruction: standing pattern from PR #2 — "don't defer fixes, don't stop". Actionable findings fixed inline; principled deferrals tracked.

| ID | Pattern | Skill | File:Line | Finding | Decision | Resolution-SHA | Date |
|----|---------|-------|-----------|---------|----------|----------------|------|
| 1 | Pattern 9: Nullability | style | server/eval/run_sd_eval.py:111 | `client: anthropic.Anthropic` typed non-optional but `None` passed on agent_sdk path | KEEP — same lie exists in `evaluator.py:81`. Fixing only sd_evaluator.py creates asymmetry; fixing both expands scope (touches algo evaluator). v0.7.5 cleanup item. | n/a | 2026-05-10 |
| 2 | Pattern 17: Naming (flippable args) | style | server/eval/run_sd_eval.py:54 | `_matches(actual, expected)` arg order silently flippable | FIX — converted to keyword-only (`_matches(*, actual, expected)`). All call sites updated. | (this commit) | 2026-05-10 |
| 3 | Class coherence (encoding semantics) | style | server/eval/sd_cases.yaml:153 | `[tag, null]` list-with-null encoding undocumented | FIX — added explicit encoding documentation to YAML header (scalar=exact, list=any-of, null-in-list=or-no-pushback). | (this commit) | 2026-05-10 |
| 4 | TV-1: Mock-only testing | test-validation | server/tests/test_sd_eval_harness.py | Plan task 3.4 specified "one mocked-Opus case round-trips"; not implemented (every `_check` test built SDEvaluatorOutput by hand, so a field rename in `evaluate()` would still pass them) | FIX — added `test_evaluate_to_check_round_trip_pass` and `_fail`. Pulls output through real `evaluate()` codepath with mocked Anthropic client, then runs `_check` on the result. Closes TV-1, SC-1, and Cross-Component #1 in one ~30-LOC test. | (this commit) | 2026-05-10 |
| 5 | TV-3: Presence-only floor | test-validation | server/tests/test_sd_eval_harness.py:28 | `len(cases) >= 15` lets a whole question's coverage be deleted silently | FIX — tightened to `>= 18` with per-question floor of 4. | (this commit) | 2026-05-10 |
| 6 | TV-5: Boundary value gaps | test-validation | server/tests/test_sd_eval_harness.py | `_check` not tested with empty / all-keys-present expected dict | KEEP — minor edge cases; existing 16 tests cover the load-bearing semantics. Not worth the noise. | n/a | 2026-05-10 |
| 7 | TV-4: Untested intentional absence | test-validation | server/eval/run_sd_eval.py:111 | agent_sdk-with-None-client path not asserted | KEEP — verifying this requires a real backend; mocked test would just verify the mock. Defer to integration coverage when CLAUDE_CODE_OAUTH_TOKEN is wired into CI. | n/a | 2026-05-10 |
| 8 | RS-3: Duplication with run_eval.py | refactoring-safety | run_sd_eval.py vs run_eval.py | ~50 lines of shared structure; could extract `run_cases(load_fn, evaluate_fn, cases, check_fn, threshold)` | KEEP — plan §"Stop conditions" line 937 explicitly forbids refactors at this stage ("STOP. Refactors at this stage compound risk for the friends-only beta. File the idea as a v1.5+ improvement and keep shipping."). Tracked as v1.5+ candidate. | n/a | 2026-05-10 |
| 9 | RS-5: Reuses private helpers | refactoring-safety | server/eval/run_sd_eval.py:30 | `_load_phases`/`_load_pushbacks` are private (`_`-prefixed) helpers from `evaluate_sd_attempt` | KEEP — promoting them to public would expand scope. The mocked round-trip test (#4) protects against renames by pulling output through `evaluate()`, which still uses the same shape. | n/a | 2026-05-10 |
| 10 | SC-1: Missing R5 (mocked round-trip) | spec-compliance | server/tests/test_sd_eval_harness.py | Plan task 3.4 stop condition unmet | FIX — see #4 above. | (this commit) | 2026-05-10 |
| 11 | SC-2: List-valued schema deviation | spec-compliance | server/eval/sd_cases.yaml + run_sd_eval.py:54 | Plan §3.1 specifies scalar expectations; impl extended to list (any-of) on 9/18 cases | FIX (accept + document) — list-valued is the right call (pin behavior bands, not arbitrary single answers). Documented encoding semantics in YAML header (#3 above). Plan amendment NOT made — v0.7-finish.md is a planning artifact, not a contract; encoding lives in `_matches` and the YAML header. | (this commit) | 2026-05-10 |
| 12 | SC-1: SDK Opus run deferred (R10) | spec-compliance | - | Plan task 3.7 "optional but recommended" not run | KEEP (deferred) — env's `ANTHROPIC_API_KEY` returns 401; same key fails `test_backend_parity` on master. Not a PR-blocker per the plan's own "optional but recommended" language. v0.7.5 follow-up: rotate API key, run `uv run python -m eval.run_sd_eval`, append result to this log. | n/a | 2026-05-10 |
| 13 | SC-3: agent_sdk backend (scope creep) | spec-compliance | server/eval/run_sd_eval.py:93 | Backend-switching not in plan (parity with `run_eval.py`) | KEEP (accept) — exact mirror of the algo eval; rejecting it would create asymmetry between two near-identical files. Defensible scope creep. | n/a | 2026-05-10 |
| 14 | SC-3: Bank-vs-cases drift test | spec-compliance | server/tests/test_sd_eval_harness.py:53 | Not in plan; catches typos before paid runs | KEEP (accept) — solidly within "smoke tests for the harness itself" spirit. High value, zero downside. | n/a | 2026-05-10 |
| 15 | Cross-component #3: Sub-agent prompt drift | spec-compliance / style | server/eval/agent-evaluator-sd-prompt.md | Bespoke "fire no_capacity_estimate when candidate jumps to architecture" rule not in production `SYSTEM_PROMPT`; drifts the sub-agent path from being a faithful proxy | FIX — removed bespoke rule. Added a "keep this in sync with sd_evaluator.py:SYSTEM_PROMPT" note as a guardrail against future drift. | (this commit) | 2026-05-10 |

## Cross-component insight applied

Findings #4 (TV-1), #10 (SC-1), and the orchestrator's Cross-Component #1 all pointed at the same root cause: `_check` rigorously unit-tested in isolation but the wiring `evaluate() → SDEvaluatorOutput → _check()` only verified by paid runs. ONE ~30-LOC mocked round-trip test closes all three. Highest-leverage fix in the batch.

## Sub-verdicts

- code-style: Comment (3 findings; 2 fixed, 1 kept with rationale)
- test-validation: Comment (4 findings; 2 fixed, 2 kept with rationale)
- refactoring-safety: Approve (no callers needed updating; duplication is a v1.5+ refactor candidate)
- spec-compliance: Comment (6 findings; 3 fixed, 3 kept with rationale)

## Deferred to v0.7.5

1. **Type signature cleanup**: widen `evaluate(client)` to `anthropic.Anthropic | None` in BOTH `evaluator.py` and `sd_evaluator.py` together. Consistency.
2. **SDK Opus eval**: rotate `ANTHROPIC_API_KEY`, run `uv run python -m eval.run_sd_eval`, append result here. Validates production forced-tool-use plumbing end-to-end.
3. **(v1.5+) Extract shared loop** between `run_eval.py` and `run_sd_eval.py` once a third eval (recommender? generator?) makes the pattern obvious.
