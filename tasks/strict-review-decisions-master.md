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
