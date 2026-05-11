# Strict Review Decision Log - PR #5 (fix/v0.7.5-evaluator-client-typing)

PR A.1 of `docs/plans/2026-05-11-whiteboard-open-issues.md`: widen `evaluate(*, client: ...)` to `anthropic.Anthropic | None` in both `whiteboard_mcp/evaluator.py` and `sd_evaluator.py`, tighten docstring, add contract-pin tests.

Closes the deferred typing cleanup from `tasks/strict-review-decisions-PR-3.md` row #1.

User instruction: standing pattern from PR #2 / PR #3 - "don't defer fixes, don't stop". Actionable findings fixed inline; principled deferrals tracked.

Initial review verdict: **Comment** (style=Approve, test-validation=Comment, refactoring-safety=Approve, spec-compliance=Approve). One actionable finding (TV-4), applied inline.

| ID | Pattern | Skill | File:Line | Finding | Decision | Resolution-SHA | Date |
|----|---------|-------|-----------|---------|----------|----------------|------|
| 1 | TV-4: Untested intentional absence | test-validation | server/tests/test_evaluator.py:204 + server/tests/test_sd_evaluator_unit.py:218 | Contract-pin tests assert return identity (`out is fixture`) but do not assert that `client=None` is propagated to the inner `evaluate_with_forced_tool` call. A future defensive default inside `evaluate()` (e.g. `client = client or get_anthropic_client()`) would silently break the agent_sdk caller's intent - building a client triggers ANTHROPIC_API_KEY errors on that backend - and these tests would still pass. | FIX - replaced the inline `lambda **kw: fixture` with a named `_fake_backend(**kw)` that captures kwargs into a `captured: dict`, then added `assert captured["client"] is None`. ~5 lines per test. | (this commit) | 2026-05-11 |
| 2 | SC-N awareness items | spec-compliance | - | Spec-compliance reviewer noted three minor deviations from the plan snippet (non-empty phases/pushbacks in the SD test fixture, slightly different docstring wording, top-level imports vs in-function imports). All three are improvements over the spec snippet; the spec is a sketch, not a contract. | KEEP - all three deviations strengthen the implementation without changing intent. No action. | n/a | 2026-05-11 |

## Sub-verdicts (final)

- code-style: Approve (no findings)
- test-validation: Approve after TV-4 fix applied (initial: Comment)
- refactoring-safety: Approve (widening a parameter type is contravariant-safe; all four production callers compile under the new signature without change)
- spec-compliance: Approve (six spec claims all verified; zero scope creep; zero coverage gaps)

## Notes for future sessions

- This PR closes PR-3 decision log row #1. The handoff (`docs/plans/2026-05-11-handoff.md`) called this out as Phase A.1 of the v0.7.5 cleanup block.
- The `test_backend_parity::test_metered_backend_returns_evaluator_output` deselect is still required (env's `ANTHROPIC_API_KEY` returns 401 on master). Not a regression.
- After merge, v0.7.5 backlog reduces to the v1.5+ shared-eval-loop refactor (PR-3 row #8) plus the Phase A.2 return-shape change in the same plan.
