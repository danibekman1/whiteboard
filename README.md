# whiteboard

Socratic interview-prep coach for FAANG-tier algo rounds (system design lands in a later phase). v0.6 ships a roadmap UI on top of the 75-question bank: topic-DAG home page, per-topic progress + recommended-next, agent-classified session outcomes feeding a per-pattern weakness profile.

## Run

```
cp .env.example .env   # paste your ANTHROPIC_API_KEY
./run.sh
```

Then open http://localhost:3000 — the home page is the topic-DAG roadmap. Click a topic to see its questions and the recommended-next pick; clicking a question (or the recommendation card) starts a coaching session at `/practice/<session_id>`.

## Bank pipeline (offline, dev-time)

The 75 questions in `coach.db` come from a generator that runs offline,
not at request time. Source of truth: `server/bank/seed/` (the 75-entry
list + per-slug optimal complexity). Generation is a 3-stage offline
batch under `server/bank/`:

```
cd server
uv run python -m bank.generate          # ~30-45 min, ~$25-40 of Opus calls
uv run python -m bank.validate          # offline; verifies generated/
uv run python -m bank.ingest            # writes coach.db (also runs at server boot)
```

Generated files (`server/bank/generated/`) are gitignored — reproducible from
`bank/seed/`. Resumability: `bank.generate` skips slugs whose JSON already
validates, so a partial run can be re-run cheaply.

### Dev fallback when API credits aren't available

If you don't have an Anthropic API key with credits handy, the generator can
also run as a sub-agent dispatch from a Claude Code session, billed against
your Claude Code subscription. The per-slug agent prompt template is at
`server/bank/agent-generator-prompt.md` — open Claude Code in the repo root
and ask it to "generate the missing slugs in bank/generated/ using
server/bank/agent-generator-prompt.md, one sub-agent per slug." The SDK path
(`bank/generator.py`) is unchanged and remains the supported flow for CI and
production.

## What's new in v0.6

- **Roadmap home page** at `/`: topic-DAG (react-flow) with per-topic status
  (mastered / in-progress / unlocked / locked) plus a right-pane detail view
  showing prereqs, the recommended-next pick, and the topic's question list.
- **`record_outcome` MCP tool** called by the outer coach at session end
  (`unaided` / `with_hints` / `partial` / `skipped` / `revisit_flagged`).
  Idempotent; bumps a per-pattern `weakness_profile` table.
- **`get_weakness_profile` MCP tool**: per-pattern miss rates, sorted desc.
- **`get_roadmap` MCP tool + `roadmap://state` resource**: full DAG payload
  (topics, edges, questions, recommendation, top-5 weakness) for the UI.
- **Heuristic recommendations** — pure Python, deterministic, no per-load
  LLM call. Five strategies in priority order: focus-topic continuation,
  weakness drill, topic step-up after prereqs cleared, difficulty step-up
  after easies cleared, fresh start. Templated justifications.
- **Topic prereqs DAG** seeded from `server/bank/seed/topic_prereqs.json`
  (17 edges across 18 topics, mirrors NeetCode's roadmap). Cycle-checked
  at boot.
- **`/practice/[id]` route** holds the chat UI (moved from `/`); `/api/start-question`
  bridges the roadmap "Start" click to a session.
- **End-session UX**: "Leave session" button (records `partial` outcome via
  the agent), session-complete banner triggered when the agent calls
  `record_outcome`.

## What works in v0.5a

- **75 algo questions** (Blind-75 sourced) with 3-level hints per step.
- **3 MCP tools**: `get_next_question`, `evaluate_attempt`, `get_hint`.
- Two-LLM split: outer Socratic coach (Next.js, streaming) + inner Opus
  evaluator with forced tool-use structured output (Python MCP server).
- Pedagogy eval: 11 golden cases sampled across the bank.
- Sessions and attempts persist across container restarts
  (`server/data/coach.db`).
- Chat history is browser-memory only — refresh loses chat (server-side
  `attempts` survive).

## What's not in v0.6 (next phases)

System design (v0.7), LLM-justified recommendations, "Try anyway?" soft-lock
on locked topics, server-side `hint_invocations` for accurate `hints_used`,
companies, multi-user / auth, hosted deployment.

## Layout

```
server/             Python MCP server (FastMCP + SQLite)
  whiteboard_mcp/   Package: db, evaluator, errors, topic_seed_loader,
                    recommend, tools/
    tools/          get_next_question, evaluate_attempt, get_hint,
                    record_outcome, get_weakness_profile, get_roadmap
  bank/             Offline question-bank pipeline
    seed/           blind75.json, topics.json, topic_prereqs.json,
                    optimal_complexity.csv (source of truth)
    schemas.py      Pydantic shape for per-question JSON
    generator.py    Opus SDK forced tool-use generation (production path)
    validator.py    Schema + correctness (subprocess) + complexity validation
    ingest.py       Reads bank/generated/*.json, upserts into coach.db
    generated/      ← gitignored: produced by bank.generate
    agent-generator-prompt.md   Sub-agent prompt template (dev fallback path)
  tests/            pytest unit + integration
  eval/             Golden-case pedagogy eval (real Opus calls)
  data/             coach.db (gitignored, volume-mounted)

web/                Next.js 16 + React 19 + TS UI
  app/              / (roadmap), /practice/[id] (chat),
                    /api/chat (SSE), /api/roadmap, /api/start-question
  lib/              anthropic.ts, mcp-client.ts, coach-prompt.ts,
                    status-colors.ts, sse.ts, types.ts
  components/       Chat, Composer, Message, ToolCallPill,
                    Roadmap, ProgressDots, QuestionCard, TopicDetail
```

## Tests

```
cd server && uv run pytest -v          # 115 tests
cd web    && npm test                   # 50 tests
```

## Pedagogy eval (real Opus calls, ~$1-2)

Production / SDK path (gold-standard signal):

```
cd server && uv run --extra dev python -m eval.run_eval
```

Requires `ANTHROPIC_API_KEY` set and `bank/generated/` populated.

### Dev fallback when API credits aren't available

Same pattern as the bank generator's dev fallback. Per-case sub-agent
prompt template lives at `server/eval/agent-evaluator-prompt.md`. Open
Claude Code in the repo root and ask:

> "Run the pedagogy eval using `server/eval/agent-evaluator-prompt.md`,
> one sub-agent per case in `server/eval/cases.yaml`. Compare each
> sub-agent's JSON output against the case's `expect:` fields and
> report PASS/FAIL per case + overall pass rate."

This is a useful sanity-check proxy (case shape + canonical-step
quality) but does NOT validate the production evaluator's
forced-tool-use plumbing — for that, you still need the SDK path.

## v0.6 end-to-end smoke

Two scripts under `scripts/` cover the v0.6 wiring:

- `scripts/smoke_v0_6_tools.py` — degraded smoke; exercises every layer
  *except* the outer-coach Anthropic loop. Verifies `/api/roadmap`,
  `/api/start-question`, `record_outcome` (idempotency, weakness bump,
  session state), and the leave-session `partial` flow. **No API key
  required.** Cleans up after itself only on success — if asserts fail,
  you may need to wipe `coach.db` manually. Run after `docker compose up`:

  ```
  python3 scripts/smoke_v0_6_tools.py
  ```

- `scripts/smoke_two_sum.py` — full real-Opus smoke; drives `/api/chat`
  through a Two Sum coaching session and watches SSE for the agent's
  `record_outcome` tool call. **Requires a valid `ANTHROPIC_API_KEY`.**
  Costs ~$0.50 of Opus. Run after `docker compose up`:

  ```
  python3 scripts/smoke_two_sum.py
  ```

The full smoke is the only thing that proves the coach prompt's discipline
rule (rule 7) actually triggers `record_outcome` at wrap_up. If you can't
run it (no API key), the unit tests + the degraded smoke + the eval case at
`server/eval/cases.yaml::two-sum-full-session-records-outcome` together
pin the contract on every other side.
