import json

import pytest
from whiteboard_mcp.db import connect, ensure_schema
from bank.ingest import ingest_bank


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "coach.db"
    conn = connect(db_path)
    ensure_schema(conn)
    yield conn
    conn.close()


# Minimal inline two-sum question used by tool-level tests so they don't
# depend on the on-disk bank (which only exists if the developer has run
# `python -m bank.generate`). Mirrors the shape of bank/generated/*.json.
_TWO_SUM_FIXTURE = {
    "slug": "two-sum",
    "title": "Two Sum",
    "statement": "Given an array of integers nums and a target, return indices summing to target.",
    "difficulty": "easy",
    "leetcode_id": 1,
    "topics": ["arrays-hashing"],
    "canonical_solution": {
        "language": "python",
        "code": "def two_sum(nums, target):\n    return [0, 1]\n",
        "time": "O(n)",
        "space": "O(n)",
    },
    "test_cases": [
        {"input": [[2, 7], 9], "expected": [0, 1]},
        {"input": [[1, 2], 3], "expected": [0, 1]},
        {"input": [[3, 3], 6], "expected": [0, 1]},
    ],
    "steps": [
        {
            "ordinal": i,
            "description": f"Step {i}: a Socratic thought about the problem.",
            "pattern_tags": ["t"],
            "hints": [
                {"level": 1, "text": f"Hint level 1 for step {i}."},
                {"level": 2, "text": f"Hint level 2 for step {i}."},
                {"level": 3, "text": f"Hint level 3 for step {i}."},
            ],
        }
        for i in range(1, 7)
    ],
}


@pytest.fixture
def db_with_two_sum(db, tmp_path):
    """db fixture pre-populated with the arrays-hashing topic and one
    bank-shape two-sum question. Use this in tool tests that exercise
    get_next_question / evaluate_attempt / get_hint."""
    db.execute("INSERT INTO topics (slug, name) VALUES (?, ?)", ("arrays-hashing", "Arrays & Hashing"))
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(_TWO_SUM_FIXTURE))
    ingest_bank(db, gen)
    return db
