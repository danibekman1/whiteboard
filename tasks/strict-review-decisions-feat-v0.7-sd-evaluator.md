# Strict Review Decisions — feat/v0.7-sd-evaluator

PR 3 of v0.7 (SD evaluator + evaluate_sd_attempt MCP tool).
First review on this branch. Resolution-SHA filled in once the fix commit lands.

| ID | Pattern | Skill | File | Finding Summary | Decision | Resolution-SHA | Date |
|----|---------|-------|------|-----------------|----------|----------------|------|
| 1  | Pattern 1: No Default Values | style | server/whiteboard_mcp/sd_evaluator.py:160 | `model: str \| None = None` on public `evaluate()` | Accepted convention — mirrors algo evaluator entry point; treat as established pattern for both | n/a | 2026-05-10 |
| 2  | Pattern 9: Nullability | style | server/whiteboard_mcp/sd_evaluator.py:43 | `pushback_triggered: str \| None = None` could be `""` | Keep nullable — None vs trigger_tag is more honest than empty-string sentinel | n/a | 2026-05-10 |
| 3  | Pattern 17: Naming | style | server/whiteboard_mcp/tools/evaluate_sd_attempt.py:64 | `_load_history` vs param `session_so_far` | Resolved — renamed to `_load_session_so_far` | 16cd841 | 2026-05-10 |
| 4  | Naming consistency | style | server/whiteboard_mcp/tools/evaluate_sd_attempt.py:80 | hard-coded `"clarify"` fallback duplicates Phase Literal | Resolved — added `DEFAULT_PHASE_FALLBACK` constant in sd_evaluator.py and imported it | 16cd841 | 2026-05-10 |
| 5  | Pattern 12: Code placement | style | server/whiteboard_mcp/sd_evaluator.py:131 | `get_anthropic_client` duplicated from algo evaluator | Resolved — extracted to `whiteboard_mcp/_anthropic.py`; both evaluators import it | 16cd841 | 2026-05-10 |
| 6  | Class coherence | style | server/whiteboard_mcp/sd_evaluator.py:25-31 | `checklist_covered` description (this-turn) contradicts SYSTEM_PROMPT (cumulative) | Resolved — field description updated to "across this turn AND prior turns (cumulative)" matching the system prompt | 16cd841 | 2026-05-10 |
| 7  | TV-3 | test-validation | server/tests/test_sd_evaluator_unit.py:90 | substring asserts on `_build_user_message` don't verify section ordering | Resolved — added `index(...)` ordering assertion for phases<pushbacks<session_so_far<candidate_message | 16cd841 | 2026-05-10 |
| 8  | TV-3 | test-validation | server/tests/test_tool_evaluate_sd_attempt.py:131 | hard-coded `"clarify"` instead of asserting `first.phase` | Resolved — assertion now reads `first.phase` dynamically | 16cd841 | 2026-05-10 |
| 9  | TV-5 | test-validation | server/tests/test_tool_evaluate_sd_attempt.py | no test for `_load_session_so_far` malformed-JSON degradation | Resolved — added `test_evaluate_sd_attempt_degrades_on_malformed_prior_evaluator_json` | 16cd841 | 2026-05-10 |
| 10 | TV-3 | test-validation | server/tests/test_tool_evaluate_sd_attempt.py:165 | `"tool_use" in result["raw"]` should be `==` exact | Resolved — exact-match assertion | 16cd841 | 2026-05-10 |
| 11 | TV-5 | test-validation | server/tests/test_tool_evaluate_sd_attempt.py | parse-failure and internal_error tests don't assert no-persistence | Resolved — added `n == 0` assertions to both | 16cd841 | 2026-05-10 |
| 12 | RS-3 | refactoring-safety | server/whiteboard_mcp/tools/evaluate_attempt.py | algo `evaluate_attempt` doesn't symmetrically reject SD sessions | Resolved (option b) — added `FIXME(v0.7-pr4)` module-docstring marker; full guard deferred per plan stop-condition #3 | 16cd841 | 2026-05-10 |
| 13 | RS-5 | refactoring-safety | server/tests/test_server_bootstrap_walks_sd_curated.py:64 | `raising=False` on SD_CURATED_DIR defeats the contract pin | Resolved — switched to `raising=True` (default) | 16cd841 | 2026-05-10 |

## Report-only items (no decision needed)

- TV-1 (mock-only `evaluate()` testing): consistent with algo evaluator; integration test deferred to v1.
- RS-5 minor (algo `evaluate_attempt` SELECT doesn't include `q.type`): would be a one-line addition once the symmetric guard lands in PR 4.
- RS-1 (slug collision across types in `ingest_bank` UPSERT): not a regression introduced here; track for v0.7 ship readiness.
