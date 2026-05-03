# Strict Review Decision Log - master (v0.5a)

| ID | Pattern | Skill | File:Line | Finding | Decision | Date |
|----|---------|-------|-----------|---------|----------|------|
| 1 | Defaults on Data Class Fields | style | server/bank/generator.py:11-19 | GenerationInput optional fields default to None hide CSV-empty rows | FIX: remove defaults, force loader to be explicit | 2026-05-03 |
| 2 | Cross-module private import | style | server/bank/generate.py:9 | _NON_RETRYABLE imported across modules breaks the privacy convention | FIX: rename to NON_RETRYABLE_ERRORS (public) | 2026-05-03 |
| 3 | Stale docstring | style | server/bank/ingest.py:1-4 | Docstring doesn't mention session.current_step_id NULLing on re-ingest | FIX: extend docstring | 2026-05-03 |
| 4 | Missing validation | style | server/bank/schemas.py:48-51 | TestCase.input allows empty list | FIX: add min_length=1 | 2026-05-03 |
| 5 | Brittle placeholder substitution | style | server/bank/correctness.py | __FN_NAME__ literal substitution can collide with candidate code | FIX: pass values via runner argv instead of source-injection | 2026-05-03 |
| 6 | Mock-only testing | test-validation | server/tests/test_bank_generator.py | Generator only tested with mocked client | KEEP: smoke run covers real-shape; cost-prohibitive in unit tests | 2026-05-03 |
| 7 | Boundary value gap | test-validation | server/tests/test_bank_correctness.py | Generic non-zero exit failure path untested | FIX: add test for SyntaxError in candidate code | 2026-05-03 |
| 8 | Boundary value gap | test-validation | server/tests/test_bank_ingest.py | Malformed JSON ingest path untested | FIX: add test for corrupt JSON file | 2026-05-03 |
| 9 | Intentional absence untested | test-validation | server/tests/test_bank_ingest.py | Test doesn't verify topic_id=NULL when primary unknown | FIX: add assertion | 2026-05-03 |
| 10 | Vestigial code | refactoring-safety | server/tests/fixtures/legacy_seeds/ | Legacy v0 seed JSONs kept but unused | FIX: delete them | 2026-05-03 |

## v0.6 sub-phase A-C round (commits 04f56ca..34291b6)

spec: docs/plans/2026-05-03-whiteboard-v0.6-roadmap.md

| ID | Pattern | Skill | File:Line | Finding | Decision | Date |
|----|---------|-------|-----------|---------|----------|------|
| 11 | Error message clarity | style | server/whiteboard_mcp/topic_seed_loader.py | warn doesn't say which side is unknown | FIX: name missing slug ('topic'/'prereq') in message | 2026-05-03 |
| 12 | Nullability + missing FK | style | server/whiteboard_mcp/db.py weakness_profile.last_seen_session | nullable + no FK | FIX: kept nullable for read-tool tests, added FK to sessions(id) + comment justifying | 2026-05-03 |
| 13 | Missing cycle validation | style | server/whiteboard_mcp/topic_seed_loader.py ingest_topic_prereqs | spec said "no cycles enforced at app layer" but no enforcement | FIX: added _assert_acyclic topo-DFS, raises ValueError on cycle | 2026-05-03 |
| 14 | Stale comment | style | server/whiteboard_mcp/db.py | comment partly outdated | FIX: tightened comment, annotated v0.5a / v0.6 inline | 2026-05-03 |
| 15 | Boundary value gap | test-validation | server/tests/test_tool_record_outcome.py | three of five outcomes untested | FIX: parametrized test over VALID_OUTCOMES | 2026-05-03 |
| 16 | Boundary value gap | test-validation | server/tests/test_tool_record_outcome.py | zero-attempts session untested | FIX: added test_record_outcome_zero_attempts_no_weakness_updates | 2026-05-03 |
| 17 | Presence-only assertion | test-validation | server/tests/test_tool_record_outcome.py | ended_at format unverified | FIX: added regex match for ISO format | 2026-05-03 |
| 18 | Boundary value gap | test-validation | server/tests/test_tool_record_outcome.py | out-of-range step_ordinal silently dropped, untested | FIX: added test pinning silent-drop behaviour | 2026-05-03 |
| 19 | Two sources of truth | spec-compliance | record_outcome.py:13 + db.py:90-91 | VALID_OUTCOMES duplicated in Python tuple + CHECK string | FIX: moved VALID_OUTCOMES to db.py; CHECK constraint built from constant; record_outcome imports it | 2026-05-03 |
| 20 | Spec wording vs behaviour | spec-compliance | record_outcome.py docstring | spec said "missed steps" but code bumps total for all attempted | FIX: tightened docstring to match code; spec wording will be revisited next round | 2026-05-03 |
| 21 | Mock-only testing | test-validation | server/tests/test_tool_record_outcome.py | unit tests mock the evaluator | KEEP: same precedent as v0.5a #6, end-to-end smoke (Task 19) covers real path | 2026-05-03 |
| 22 | New tool not yet wired into coach prompt | refactoring-safety | record_outcome MCP tool | coach prompt doesn't tell agent to call it | DEFER: scope-deferred to Task 11 by plan | 2026-05-03 |
| 23 | New tool not yet wired into web | refactoring-safety | record_outcome / get_weakness_profile MCP tools | web client doesn't call them | DEFER: scope-deferred to Tasks 12-18 by plan | 2026-05-03 |

## v0.6 sub-phase D round (commits 41a8b8b..fb052fc)

| ID | Pattern | Skill | File:Line | Finding | Decision | Date |
|----|---------|-------|-----------|---------|----------|------|
| 24 | Spec deviation | spec-compliance | server/whiteboard_mcp/recommend.py focus-topic branch | "sister topic just mastered" justification template missing (spec line 93) | FIX: branch on solved=0+mastered prereqs to emit "start {topic} - you nailed {prereq} (n/m)" | 2026-05-03 |
| 25 | Spec deviation | spec-compliance | server/whiteboard_mcp/recommend.py | strategy 4 (difficulty step-up) only fired inside focus branch, missing globally | FIX: added top-level strategy 4 pass after step-up, before fresh-start | 2026-05-03 |
| 26 | Stale numbered comments | style | server/whiteboard_mcp/recommend.py | 1, 2, 3, 5 (skip 4) didn't match strategy ladder | FIX: added "4. Difficulty step-up" + "6. Nothing left" comments | 2026-05-03 |
| 27 | Untested intentional absence | test-validation | server/tests/test_recommend.py test_returns_none_when_everything_cleared | accepted both None and fallback (vacuous) | FIX: pinned to `assert recommend_next(db) is None` | 2026-05-03 |
| 28 | Coverage gap | test-validation | server/tests/test_recommend.py | "you nailed prereq" justification untested | FIX: added test_focus_topic_starting_fresh_credits_mastered_prereq | 2026-05-03 |
| 29 | Coverage gap | test-validation | server/tests/test_recommend.py | difficulty step-up branch (no focus) untested | FIX: added test_difficulty_step_up_fires_without_focus | 2026-05-03 |
| 30 | LIKE substring on JSON column | style | recommend.py _question_with_pattern | LIKE %"tag"% on json-encoded pattern_tags | DEFER: parameter-bound (no SQLi); pattern_tag values are bank-controlled; revisit with json_each in v0.7 | 2026-05-03 |
| 31 | N+1 select | style | tools/get_roadmap.py | per-topic SELECT name in loop | DEFER: 18 topics, trivial; fold into _topic_status query if revisited | 2026-05-03 |
| 32 | focus_topic_slug not validated | style | recommend.py | unknown slug silently falls through | DEFER: not harmful; spec doesn't require explicit error | 2026-05-03 |
