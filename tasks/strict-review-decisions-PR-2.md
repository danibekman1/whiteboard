# Strict Review Decision Log - PR #2 (fix/v0.7-pr5.1-phase-tracker-sync)

PR 5.1 hotfix: SD phase tracker auto-updates after each tool_result.
First strict review on this branch. Verdict: Comment (no blockers).

User instruction: "don't defer fixes and don't stop". Actionable findings
fixed in the same branch before final commit. Findings #2 (defensible
null-branch no-op) and #5 (speculative two-sources-of-truth) kept as-is.

| ID | Pattern | Skill | File:Line | Finding | Decision | Resolution-SHA | Date |
|----|---------|-------|-----------|---------|----------|----------------|------|
| 1 | Phase-set duplication | style | web/components/Chat.tsx:10-21 | PHASE_ORDINAL silently adds a 4th hard-coded site; server-side tally comment claimed only 3. Cheap option taken (update tally). Upstream option (server returns `{phase, ordinal}`) deferred to v0.7.5 — out of scope for hotfix. | FIX (option 1): updated `tools/get_session.py:19-24` to mention the 4th site and `Chat.tsx:11-13` to point at the canonical mirror. | (this commit) | 2026-05-10 |
| 2 | Pattern 9: Nullability | style | web/components/Chat.tsx:117 | `setSession((s) => s ? ... : s)` no-op on null session correct but unasserted | KEEP — defensible; null session means SD pane never rendered, the failure mode is benign and the test surface would be contrived. | n/a | 2026-05-10 |
| 3 | TV-3: Presence-only assertion | test-validation | Chat.phase-sync.test.tsx:124 | Algo test asserts no `[data-phase]` but doesn't assert current_phase unchanged | FIX (rolled into #4): the new parametric guard tests assert all 5 phase chips stay `data-current="false"` after malformed payloads, which is a stronger version of the same invariant. | (this commit) | 2026-05-10 |
| 4 | TV-5: Boundary value gaps | test-validation | Chat.phase-sync.test.tsx | Discriminator's 4 guards (result&&, typeof object, typeof phase===string, phase in PHASE_ORDINAL) each individually unasserted | FIX: added `test.each` parametric block covering null result, missing phase, non-string phase, and unknown phase string. 4 new cases. | (this commit) | 2026-05-10 |
| 5 | RS-3: New code path | refactoring-safety | web/components/Chat.tsx:108-118 | After fix, current_phase has two sources of truth (initial GET + SSE); no test asserts they agree | KEEP — they agree by construction (both derive from evaluator_json). Worst-case failure is "tracker shows wrong phase briefly", not data corruption. Contrived to test without real backend. Note for v0.7.5 review. | n/a | 2026-05-10 |
| 6 | Comment accuracy | style | web/components/Chat.tsx:12-14 | Comment pointed at `sd_evaluator.py` but actual mirror is `tools/get_session.py:_PHASE_ORDINAL` | FIX: corrected comment to name the actual mirror. | (this commit) | 2026-05-10 |

## Cross-component insight applied

Findings #3 and #4 share the same root: untested guard tightness. Folded #3 into the parametric solution for #4 (5-chip data-current sweep). One test block, both findings closed.

## Deferred (v0.7.5 candidate)

**Upstream phase-set duplication fix** (finding #1, option 2): Have `evaluate_sd_attempt` return `current_phase: {phase, ordinal}` instead of `phase: string`, so the client never recomputes the ordinal and PHASE_ORDINAL can be deleted from `Chat.tsx`. ~1-day effort touching `sd_evaluator.py`'s return type, the SSE event schema, and Chat.tsx. Not a hotfix concern. File before PR 6b lands and bakes the four-site coupling deeper.
