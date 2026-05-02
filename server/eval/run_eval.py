"""Golden-case eval for the inner evaluator.

For each case: load the canonical steps for the question, run the inner
evaluator over the simulated user_text, assert the classification matches
expectations. Calls Opus directly (not via /api/chat) because we're testing
the evaluator, not the outer coach.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import yaml

from whiteboard_mcp.db import connect, ensure_schema
from whiteboard_mcp.evaluator import evaluate, get_anthropic_client
from whiteboard_mcp.seed_loader import ingest_seeds

SEED_DIR = Path(__file__).parent.parent / "whiteboard_mcp" / "seed"
CASES = Path(__file__).parent / "cases.yaml"


def _load_question(conn, slug: str):
    q = conn.execute(
        "SELECT id, statement FROM questions WHERE slug = ?", (slug,)
    ).fetchone()
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

    cases = yaml.safe_load(CASES.read_text())
    conn = connect(":memory:")
    ensure_schema(conn)
    ingest_seeds(conn, SEED_DIR)
    client = get_anthropic_client()

    failures = 0
    for c in cases:
        statement, steps = _load_question(conn, c["question_slug"])
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
