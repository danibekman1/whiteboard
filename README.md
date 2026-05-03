# whiteboard

Socratic interview-prep coach for FAANG-tier algo rounds (system design lands in a later phase). v0.5a scope: 75 Opus-generated Blind-75 questions with 3-level hints, two-LLM split (outer coach in Next.js + inner Opus evaluator in the MCP server), chat-only UI.

## Run

```
cp .env.example .env   # paste your ANTHROPIC_API_KEY
./run.sh
```

Then open http://localhost:3000 and say "let's do Two Sum".

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

## What works in v0.5a

- **75 algo questions** (Blind-75 sourced) with 3-level hints per step.
- **3 MCP tools**: `get_next_question`, `evaluate_attempt`, `get_hint`.
- Two-LLM split: outer Socratic coach (Next.js, streaming) + inner Opus
  evaluator with forced tool-use structured output (Python MCP server).
- Topic tagging (flat — DAG / prereqs come in a later phase).
- Pedagogy eval: 11 golden cases sampled across the bank.
- Sessions and attempts persist across container restarts
  (`server/data/coach.db`).
- Chat history is browser-memory only — refresh loses chat (server-side
  `attempts` survive).

## What's not in v0.5a

System design, weakness profile, roadmap UI, companies, prompt caching,
chat-history persistence.

## Layout

```
server/             Python MCP server (FastMCP + SQLite)
  whiteboard_mcp/   Package: db, evaluator, errors, topic_seed_loader, tools/
  bank/             Offline question-bank pipeline
    seed/           blind75.json, topics.json, optimal_complexity.csv (source of truth)
    schemas.py      Pydantic shape for per-question JSON
    generator.py    Opus SDK forced tool-use generation (production path)
    validator.py    Schema + correctness (subprocess) + complexity validation
    ingest.py       Reads bank/generated/*.json, upserts into coach.db
    generated/      ← gitignored: produced by bank.generate
    agent-generator-prompt.md   Sub-agent prompt template (dev fallback path)
  tests/            pytest unit + integration
    fixtures/legacy_seeds/   v0 hand-crafted JSONs (kept for regression)
  eval/             Golden-case pedagogy eval (real Opus calls)
  data/             coach.db (gitignored, volume-mounted)

web/                Next.js 16 + React 19 + TS chat UI
  app/api/chat/     SSE route running the outer-coach loop
  lib/              anthropic.ts, mcp-client.ts, coach-prompt.ts, sse.ts, types.ts
  components/       Chat, Composer, Message, ToolCallPill
```

## Tests

```
cd server && uv run pytest -v          # 76 tests
cd web    && npm test                   # 19 tests
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
