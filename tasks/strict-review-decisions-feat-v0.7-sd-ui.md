# Strict Review Decision Log - feat/v0.7-sd-ui

PR 5 of v0.7 (web SD UI: RoadmapTabs + SDList + SDQuestionPane + Chat dispatch +
/api/chat question_type + coach prompt dispatch & SD discipline).
Strict review run: 2026-05-10 (Comment verdict, no blockers).

User instruction: "don't defer fixes and don't stop". All 12 findings fixed in
the same branch before opening the PR. Cross-component insights collapsed the
12 findings into 3 logical fix groups (typing / wrapper / tests + defaults).

| ID | Pattern | Skill | File:Line | Finding | Decision | Date |
|----|---------|-------|-----------|---------|----------|------|
| 1 | Pattern 17: Naming Will Age Poorly | style | web/lib/status-colors.ts:12 | OUTCOME_PILL keyed on string with silent fallback | FIX: introduced exported `Outcome` union; OUTCOME_PILL is now `Record<Outcome, string>`; `statusPillClass(outcome: Outcome)` no longer falls back. | 2026-05-10 |
| 2 | Pattern 17: Naming Will Age Poorly | style | web/components/SDList.tsx:11 | latest_outcome typed as `string \| null` | FIX: retyped to `Outcome \| null`; same retype propagated to web/app/page.tsx SDQuestion type. | 2026-05-10 |
| 3 | Pattern 9: Nullability Justification | style | web/components/Chat.tsx:37 | `pushbacks?: ...[]` on SessionMeta with no consumer | FIX: dropped from SessionMeta. Spec assigns the consume-side to the coach via get_session server-side, not the browser. Re-add only when a real consumer ships. | 2026-05-10 |
| 4 | Pattern 17: Naming Will Age Poorly | style | web/components/RoadmapTabs.tsx:5-6 | `VALID: Tab[]` mirrors the `Tab` union manually | FIX: made `VALID` a `const` tuple and derived `Tab = (typeof VALID)[number]`; one source of truth for the tab list. | 2026-05-10 |
| 5 | Pattern 12: Code Placement | style | web/components/Chat.tsx:13-28,154-162 | AlgoQuestion/SDQuestion types and the question.type dispatch live in Chat.tsx | FIX: created `web/components/QuestionPane.tsx` wrapper; types and dispatch live there. Chat.tsx imports `QuestionPane`, `QuestionMeta`, `CurrentPhase` and renders a single `<QuestionPane question=... currentPhase=... />`. | 2026-05-10 |
| 6 | TV-5: Boundary Value Gaps | test-validation | web/components/__tests__/SDList.test.tsx | no test for latest_outcome pill render path | FIX: added test asserting the green pill class renders for outcome='unaided' and that no pill renders for null outcomes. | 2026-05-10 |
| 7 | TV-5: Boundary Value Gaps | test-validation | web/app/api/chat/route.ts:71-78 | no test asserting "Current question_type:" injection | FIX: extracted `buildSystemPrompt` as a pure function from runLoop; added 5 unit tests in web/app/api/chat/__tests__/route.test.ts asserting bare/session-only/SD/algo branches and line ordering. Also extended vitest include glob to `app/**/__tests__/**/*.test.ts`. | 2026-05-10 |
| 8 | TV-5: Boundary Value Gaps | test-validation | web/components/Chat.tsx:84-89 | no test asserting question_type in /api/chat POST body | FIX: added Chat.test.tsx that mocks fetch, renders Chat with an SD and an algo session, submits a turn, and asserts the recorded POST body has `question_type: "system_design"` / `question_type: "algo"`. | 2026-05-10 |
| 9 | RS-4: Deleted Code Not Replaced | refactoring-safety | web/components/Chat.tsx:37 | pushbacks field with no consumer | FIX: same as #3 (removed). | 2026-05-10 |
| 10 | RS-3: New Code Path Missing From Existing Callers | refactoring-safety | web/app/page.tsx:109 | sd_questions consumed without defensive `?? []` | FIX: `<SDList questions={data.sd_questions ?? []} ... />` so a stale browser tab against an older server falls into SDList's empty-state instead of crashing. | 2026-05-10 |
| 11 | SC-2: Wrong Approach | spec-compliance | web/components/Chat.tsx:154-162 | Spec §6 calls for a QuestionPane wrapper; implementation puts dispatch inline | FIX: same as #5 (restored the wrapper). | 2026-05-10 |
| 12 | SC-4: Ambiguous Design | spec-compliance | web/components/Chat.tsx:37 | spec doesn't say what consumes pushbacks on the browser | FIX: same as #3 (dropped from browser type). | 2026-05-10 |

## Awareness items (not fixed - acknowledged)

- **TV-3 (Presence-Only Assertions) on coach-prompt SD tests:** the new tests use regex matches against `COACH_SYSTEM_PROMPT`, which verify the words exist but not the prompt's behavioral effect. Acceptable for static-prompt content tests; an integration test against the live model is the only realistic alternative and is out of scope for v0.7.
- **Pattern 15 (E2E Tests):** no Playwright E2E covering the tab toggle / SD click-through / question_type round-trip. Manual smoke (Task 9 step 4) is the v0.7 substitute. E2E infrastructure is a future investment.
