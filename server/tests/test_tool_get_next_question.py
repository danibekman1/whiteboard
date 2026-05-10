import json
from pathlib import Path

import pytest

from whiteboard_mcp.tools.get_next_question import get_next_question
from bank.ingest import ingest_bank


def test_returns_session_with_question(db_with_two_sum):
    out = get_next_question(db_with_two_sum, slug="two-sum")
    assert "session_id" in out
    assert out["question"]["slug"] == "two-sum"
    assert out["question"]["title"] == "Two Sum"
    assert "Given an array" in out["question"]["statement"]
    # Crucial: canonical steps NEVER returned to caller.
    assert "steps" not in out["question"]
    assert "canonical" not in str(out).lower()


def test_creates_session_row(db_with_two_sum):
    out = get_next_question(db_with_two_sum, slug="two-sum")
    sid = out["session_id"]
    row = db_with_two_sum.execute(
        "SELECT * FROM sessions WHERE id = ?", (sid,)
    ).fetchone()
    assert row is not None
    assert row["current_step_id"] is None  # nothing attempted yet


def test_random_when_no_slug(db_with_two_sum, tmp_path):
    """With multiple questions in the bank, random selection picks one of them."""
    # Seed a second slug for randomness.
    db_with_two_sum.execute("INSERT INTO topics (slug, name) VALUES (?, ?)", ("dp-1d", "1-D DP"))
    extra = {
        "slug": "climbing-stairs", "title": "Climbing Stairs",
        "statement": "Count distinct ways to climb n stairs taking 1 or 2 steps.",
        "difficulty": "easy", "leetcode_id": 70,
        "topics": ["dp-1d"],
        "canonical_solution": {
            "language": "python",
            "code": "def climbing_stairs(n):\n    a, b = 1, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
            "time": "O(n)", "space": "O(1)",
        },
        "test_cases": [
            {"input": [2], "expected": 2},
            {"input": [3], "expected": 3},
            {"input": [5], "expected": 8},
        ],
        "steps": [
            {"ordinal": i, "description": f"Step {i}: think about the recurrence.",
             "pattern_tags": [], "hints": [
                 {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"},
             ]} for i in range(1, 4)
        ],
    }
    gen = tmp_path / "more"
    gen.mkdir()
    (gen / "climbing-stairs.json").write_text(json.dumps(extra))
    ingest_bank(db_with_two_sum, gen)

    out = get_next_question(db_with_two_sum)
    assert out["question"]["slug"] in {"two-sum", "climbing-stairs"}


def test_unknown_slug_returns_error(db_with_two_sum):
    out = get_next_question(db_with_two_sum, slug="nope")
    assert out["error"] == "not_found"
    assert out["entity"] == "question"
    assert out["value"] == "nope"


def test_empty_bank_returns_error(db):
    """No algo questions in the bank -> not_found keyed on the type filter.
    Pre-PR-4 the error was {by:'*', value:'(empty bank)'}; with the type
    filter we surface which type came up empty so the caller can distinguish
    a missing-bank error from a missing-SD error."""
    out = get_next_question(db)
    assert out == {
        "error": "not_found",
        "entity": "question",
        "by": "type",
        "value": "algo",
    }
