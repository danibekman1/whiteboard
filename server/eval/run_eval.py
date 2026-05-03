"""Golden-case eval for the inner evaluator (production / SDK path).

For each case: load the canonical steps for the question (from the bank
ingested into a fresh in-memory DB), run the inner evaluator over the
simulated user_text, assert the classification matches expectations.
Calls Opus directly (not via /api/chat) because we're testing the
evaluator, not the outer coach.

Requires:
- ANTHROPIC_API_KEY set (the inner evaluator goes through the SDK)
- bank/generated/ populated (run `python -m bank.generate` first)

Dev fallback (no API credits): the eval can also be run by an
orchestrating Claude Code session dispatching one sub-agent per case via
the prompt template at `eval/agent-evaluator-prompt.md`, billed against
the developer's Claude Code subscription. That path uses free-form JSON
output (not forced tool-use), so it's a sanity-check proxy, not a
validation of the production evaluator's tool-use plumbing.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import yaml

from whiteboard_mcp.db import connect, ensure_schema
from whiteboard_mcp.evaluator import evaluate, get_anthropic_client
from whiteboard_mcp.topic_seed_loader import ingest_topics
from bank.ingest import ingest_bank

ROOT = Path(__file__).parent.parent
TOPICS_SEED = ROOT / "bank" / "seed" / "topics.json"
BANK_DIR = ROOT / "bank" / "generated"
CASES = Path(__file__).parent / "cases.yaml"


def _load_question(conn, slug: str):
    q = conn.execute(
        "SELECT id, statement FROM questions WHERE slug = ?", (slug,)
    ).fetchone()
    if not q:
        raise KeyError(f"question {slug!r} not found in bank")
    steps = [
        {"ordinal": r["ordinal"], "description": r["description"]}
        for r in conn.execute(
            "SELECT ordinal, description FROM steps WHERE question_id = ? ORDER BY ordinal",
            (q["id"],),
        ).fetchall()
    ]
    return q["statement"], steps


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 2
    if not BANK_DIR.exists() or not any(BANK_DIR.glob("*.json")):
        print(
            f"{BANK_DIR} is empty - run `python -m bank.generate` first",
            file=sys.stderr,
        )
        return 2

    cases = yaml.safe_load(CASES.read_text())
    conn = connect(":memory:")
    ensure_schema(conn)
    ingest_topics(conn, TOPICS_SEED)
    ingest_bank(conn, BANK_DIR)
    client = get_anthropic_client()

    failures = 0
    for c in cases:
        try:
            statement, steps = _load_question(conn, c["question_slug"])
        except KeyError as e:
            print(f"SKIP {c['name']}: {e}")
            continue
        try:
            out = evaluate(
                client=client,
                question_statement=statement,
                canonical_steps=steps,
                user_text=c["user_text"],
            )
        except Exception as e:
            print(f"FAIL {c['name']}: evaluator raised {e!r}")
            failures += 1
            continue

        ok = True
        msgs: list[str] = []
        for k, v in c["expect"].items():
            actual = getattr(out, k)
            if actual != v:
                ok = False
                msgs.append(f"    {k}: expected {v!r}, got {actual!r}")
        status = "PASS" if ok else "FAIL"
        print(f"{status} {c['name']}")
        if not ok:
            for m in msgs:
                print(m)
            failures += 1

    print(f"\n{len(cases) - failures}/{len(cases)} passed.")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
