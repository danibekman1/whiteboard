# Strict Review Decision Log - feat/v0.7-sd-curated

| ID | Pattern | Skill | File:Line | Finding | Decision | Date |
|----|---------|-------|-----------|---------|----------|------|
| 1 | S-13: Unnecessary Wrappers | style | bank/validate.py:54-63 | Adapter from ValidationResult to ValidationReport | FIX: change sd_validator to return ValidationReport directly; remove adapter | 2026-05-10 |
| 2 | S-9: Nullability / shape divergence | style | bank/sd_validator.py:18-21 | error: str \| None vs sibling failures: list[str] | FIX: collapsed by S-13 fix - same change unifies the shape | 2026-05-10 |
| 3 | TV-3: Untested CLI dispatch | test | bank/validate.py | _peek_type routing has no integration test | FIX: add tests/test_validate_cli.py covering algo + SD routing on a mixed dir | 2026-05-10 |
| 4 | TV-3: Untested ingest overlay | test | bank/ingest.py:179-183 | sd_curated walk in _cli has no test | FIX: add tests/test_ingest_cli.py asserting curated rows reach DB | 2026-05-10 |
| 5 | RS-2: Exit code behavior change | refactoring | bank/validate.py:49-51 | empty dir return 2 -> 0 regression risk | FIX: return 2 only when no files exist at all; 0 when filter narrows from N>0 to 0 | 2026-05-10 |
| 6 | RS-1: Double-count edge case | refactoring | bank/ingest.py:178-184 | n bumped twice on slug overlap | FIX: print actual COUNT(*) FROM questions instead of summing _n_ across two calls | 2026-05-10 |
| 7 | SC-2: Spec signature mismatch | spec | bank/sd_validator.py:23 | validate_one(path) vs spec validate_one(raw, path) | KEEP: validate_one(path) is a cleaner public API (caller doesn't pre-parse); spec pseudo-code was illustrative. The unified ValidationReport return type addresses the spirit of SC-2 | 2026-05-10 |
