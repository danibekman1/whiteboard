# whiteboard

Socratic interview-prep coach for FAANG-tier algo and (eventually) system-design rounds. v0 is week-1 scope: 5 hand-crafted algo questions, two-LLM split (outer coach in Next.js + inner evaluator in the MCP server), chat-only UI.

## Run

```
cp .env.example .env   # paste your ANTHROPIC_API_KEY
./run.sh
```

Then open http://localhost:3000 and say "let's do Two Sum".

## What works in v0

- 5 questions: Two Sum, Valid Parentheses, Reverse Linked List, Binary Search, Climbing Stairs.
- 2 MCP tools: `get_next_question`, `evaluate_attempt`.
- Two-LLM split: outer Socratic coach (Next.js, streaming) + inner Opus evaluator with forced tool-use structured output (Python MCP server).
- Sessions and attempts persist across container restarts (`server/data/coach.db`).
- Chat history is browser-memory only - refresh loses chat (server-side `attempts` survive).

## What's not in v0

Hints, weakness profile, roadmap UI, system design, companies, question bank pipeline, prompt caching, chat-history persistence.

## Layout

```
server/             Python MCP server (FastMCP + SQLite)
  whiteboard_mcp/   Package: db, evaluator, errors, tools/, seed/
  tests/            pytest unit + integration
  eval/             Golden-case pedagogy eval (real Opus calls)
  data/             coach.db (gitignored, volume-mounted)

web/                Next.js 16 + React 19 + TS chat UI
  app/api/chat/     SSE route running the outer-coach loop
  lib/              anthropic.ts, mcp-client.ts, coach-prompt.ts, sse.ts, types.ts
  components/       Chat, Composer, Message, ToolCallPill
```

## Tests

```
cd server && uv run pytest -v          # 34 tests
cd web    && npm test                   # 16 tests
```

## Pedagogy eval (real Opus calls, costs a few cents)

```
cd server && uv run --extra dev python -m eval.run_eval
```
