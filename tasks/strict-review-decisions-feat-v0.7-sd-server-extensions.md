# Strict Review Decisions - feat/v0.7-sd-server-extensions

PR 4 of v0.7 (get_session/get_roadmap SD extensions + get_hint rejection +
get_next_question type filter + scenario_tag column + not_supported_for_sd
error helper).

Spec: `docs/plans/2026-05-08-whiteboard-v0.7-system-design.md` §3 (tool surface)
Plan: `docs/plans/2026-05-10-whiteboard-v0.7-pr4-server-extensions.md`

| ID | Pattern | Skill | File:Line | Finding | Decision | Date | Resolution-SHA |
|----|---------|-------|-----------|---------|----------|------|----------------|
| 1 | S-1: Default at API | style | server/whiteboard_mcp/server.py:68, server/whiteboard_mcp/tools/get_next_question.py:24 | `type='algo'` default at MCP surface violates "no defaults at API level" | FIXED: `type: str \| None = None`; business logic resolves None -> 'algo' for v0.6 back-compat | 2026-05-10 | 73c4bd2 |
| 2 | S-2: type shadows builtin | style | server/whiteboard_mcp/tools/get_next_question.py:24 | Param name `type` shadows builtin in function body | FIXED: rename to `qtype` inside function; MCP-public param unchanged | 2026-05-10 | 73c4bd2 |
| 3 | S-3: Constant naming | style | server/whiteboard_mcp/tools/get_roadmap.py:89 | `DIFF_ORDER` UPPER_CASE inside function | FIXED: hoisted to module-level `_DIFF_ORDER` | 2026-05-10 | 73c4bd2 |
| 4 | S-4: Stale comment + re-query | style | server/whiteboard_mcp/tools/get_session.py:102 | Comment claims sd_* table avoidance but scenario_tag is on questions | FIXED: folded scenario_tag into main SELECT; replaced comment with spec-§3 rationale | 2026-05-10 | 73c4bd2 |
| 5 | TV-6: Lenient pushback count | test-validation | server/tests/test_tool_get_session_sd.py:40 | `>= 3` should be `== 5` for deterministic curated bank | FIXED: pinned to ==5 + content anchor on no_capacity_estimate | 2026-05-10 | 73c4bd2 |
| 6 | TV-3: Presence-only pushback shape | test-validation | server/tests/test_tool_get_session_sd.py:42 | No assertion on response text content | FIXED: added text-prefix assertion against curated source | 2026-05-10 | 73c4bd2 |
| 7 | TV-6: Lenient subset on roadmap | test-validation | server/tests/test_tool_get_roadmap_sd.py:34 | `<=` should be `==` for deterministic bank | FIXED: pinned to exact set equality | 2026-05-10 | 73c4bd2 |
| 8 | TV-3: Either-or invalid_type | test-validation | server/tests/test_tool_get_next_question_type_filter.py:84 | Asserts `in (a, b)` instead of pinning the actual contract | FIXED: pinned to exact not_found dict shape | 2026-05-10 | 73c4bd2 |
| 9 | SC-1: scenario_tag omission | spec-compliance | server/whiteboard_mcp/tools/get_session.py:108 | Spec says null-when-empty, code omitted the key | FIXED: SD sessions always emit `scenario_tag` (value or null); algo still omits | 2026-05-10 | 73c4bd2 |
| 10 | SC-2: not_supported_for_sd shape | spec-compliance | server/whiteboard_mcp/errors.py:46 | Implementation richer than spec (3 keys vs 1) | KEEP: deliberate enrichment - tool/message keys help the coach prompt route the error; called out in PR description | 2026-05-10 | n/a |
| 11 | SC-3: type filter default | spec-compliance | server/whiteboard_mcp/tools/get_next_question.py:24 | Spec says "filter", code defaulted to algo | FIXED: same fix as S-1 - `None` default with business-logic fallback | 2026-05-10 | 73c4bd2 |

## Awareness items addressed

- TV-5 boundary gap on unknown phase string: added test `test_get_session_sd_handles_unknown_phase_string_gracefully`.
- Phase Literal "aligned sites" comment: now lists three sites (sd_phases CHECK, sd_evaluator.Phase, bank/sd_schemas.Phase).

## Awareness items deferred

- `_ingest_algo` doesn't touch `scenario_tag` on re-ingest. No realistic data flow today (slug type doesn't flip). Future ON CONFLICT-clause sweep when we add cross-type slug renames or similar.
- `get_roadmap` sd_questions sort order is implementation choice, not in spec. Useful for UI; flag for spec update next time §3 is touched.
