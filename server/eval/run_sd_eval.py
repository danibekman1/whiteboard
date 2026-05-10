"""Golden-case eval for the SD inner evaluator (production / SDK path).

Mirrors eval/run_eval.py. For each case: load the question's phases,
checklists, and pushbacks from a fresh in-memory DB seeded with the
curated SD content; run the SD evaluator with empty session_so_far over
the simulated user_text; assert classification matches expectations.

Backends mirror run_eval.py: api (default, calls Anthropic SDK directly)
or agent_sdk (constructs an SDK MCP server, billed against
CLAUDE_CODE_OAUTH_TOKEN's Claude Code subscription).

The 3 curated SD questions live in bank/seed/sd_curated/ - committed to
git, always present, no `python -m bank.generate_sd` dependency.

Dev fallback (no API credits): orchestrating Claude Code session dispatches
one sub-agent per case via eval/agent-evaluator-sd-prompt.md, billed
against Claude Code subscription. Sub-agent path uses free-form JSON
(not forced tool-use), so it's a sanity proxy."""
from __future__ import annotations
import os
import sys
from pathlib import Path

import yaml

from whiteboard_mcp.db import connect, ensure_schema
from whiteboard_mcp._anthropic import get_anthropic_client
from whiteboard_mcp.sd_evaluator import SDEvaluatorOutput, evaluate
from whiteboard_mcp.topic_seed_loader import ingest_topics
from whiteboard_mcp.tools.evaluate_sd_attempt import _load_phases, _load_pushbacks
from bank.ingest import ingest_bank

ROOT = Path(__file__).parent.parent
TOPICS_SEED = ROOT / "bank" / "seed" / "topics.json"
SD_CURATED = ROOT / "bank" / "seed" / "sd_curated"
CASES = Path(__file__).parent / "sd_cases.yaml"

# Threshold per the design risk register (docs/plans/2026-05-08-...-system-design.md
# §8). Below this, the harness exits non-zero so CI / dev runs are loud.
PASS_THRESHOLD = 85.0


def _load_question(conn, slug: str) -> tuple[str, list[dict], list[dict]]:
    q = conn.execute(
        "SELECT id, statement FROM questions WHERE slug = ?", (slug,)
    ).fetchone()
    if not q:
        raise KeyError(f"SD question {slug!r} not found in curated bank")
    phases = _load_phases(conn, q["id"])
    pushbacks = _load_pushbacks(conn, q["id"])
    return q["statement"], phases, pushbacks


def _matches(actual, expected) -> bool:
    """Match semantics: scalar expected -> exact equality; list expected ->
    any-of (actual must be in the list). Lets cases with genuinely
    defensible alternatives (e.g. nudge vs press_on_missing on incomplete
    phases) assert a band rather than picking one arbitrarily."""
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def _check(name: str, expected: dict, actual: SDEvaluatorOutput) -> list[str]:
    """Return list of failure messages; empty if pass.

    Phase / suggested_move / pushback_triggered are asserted only when the
    case explicitly lists them. Each value may be a scalar (exact match)
    or a list (any-of). checklist_covered is intentionally not asserted
    here - the model legitimately decomposes coverage differently across
    runs and a strict assertion would be flaky."""
    fails = []
    if "phase" in expected and not _matches(actual.phase, expected["phase"]):
        fails.append(f"phase: expected {expected['phase']!r}, got {actual.phase!r}")
    if "suggested_move" in expected and not _matches(
        actual.suggested_move, expected["suggested_move"]
    ):
        fails.append(
            f"suggested_move: expected {expected['suggested_move']!r}, "
            f"got {actual.suggested_move!r}"
        )
    if "pushback_triggered" in expected and not _matches(
        actual.pushback_triggered, expected["pushback_triggered"]
    ):
        fails.append(
            f"pushback_triggered: expected {expected['pushback_triggered']!r}, "
            f"got {actual.pushback_triggered!r}"
        )
    return fails


def main() -> int:
    backend = os.environ.get("CHAT_BACKEND", "api")
    if backend == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set (api backend)", file=sys.stderr)
        return 2
    if backend == "agent_sdk" and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("CLAUDE_CODE_OAUTH_TOKEN not set (agent_sdk backend)", file=sys.stderr)
        return 2
    if not SD_CURATED.exists() or not any(SD_CURATED.glob("*.json")):
        print(f"{SD_CURATED} is empty - curated SD content missing", file=sys.stderr)
        return 2

    cases = yaml.safe_load(CASES.read_text())
    conn = connect(":memory:")
    ensure_schema(conn)
    ingest_topics(conn, TOPICS_SEED)
    ingest_bank(conn, SD_CURATED)
    # On the agent_sdk backend the evaluator constructs its own SDK MCP
    # server and ignores `client`. Build one only when we'll use it.
    client = get_anthropic_client() if backend == "api" else None

    total = 0
    failures = 0
    for c in cases:
        total += 1
        try:
            statement, phases, pushbacks = _load_question(conn, c["question_slug"])
        except KeyError as e:
            print(f"FAIL {c['name']}: {e}")
            failures += 1
            continue

        try:
            actual = evaluate(
                client=client,
                question_statement=statement,
                phases=phases,
                pushbacks=pushbacks,
                session_so_far=[],
                user_text=c["user_text"],
            )
        except Exception as e:
            print(f"FAIL {c['name']}: evaluator raised {e!r}")
            failures += 1
            continue

        fails = _check(c["name"], c["expect"], actual)
        if fails:
            failures += 1
            print(f"FAIL {c['name']}:")
            for f in fails:
                print(f"  - {f}")
        else:
            print(f"PASS {c['name']}")

    pass_rate = (total - failures) / total * 100 if total else 0
    print(f"\n{total - failures}/{total} pass ({pass_rate:.1f}%)")
    return 0 if pass_rate >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
