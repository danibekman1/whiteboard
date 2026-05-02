import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from whiteboard_mcp.db import connect, ensure_schema
from bank.ingest import ingest_bank
from whiteboard_mcp.tools.get_next_question import get_next_question
from whiteboard_mcp.tools.evaluate_attempt import evaluate_attempt
from whiteboard_mcp.tools.get_hint import get_hint
from whiteboard_mcp.evaluator import EvaluatorOutput


def _seed_topics(conn):
    conn.execute("INSERT INTO topics (slug, name) VALUES (?, ?)", ("arrays-hashing", "Arrays & Hashing"))


def _bootstrap_with_two_sum(conn, tmp_path):
    """Helper: ensure topics + write a two-sum question to a temp generated/ + ingest."""
    _seed_topics(conn)
    q = {
        "slug": "two-sum", "title": "Two Sum",
        "statement": "Given an array, find a pair summing to target.",
        "difficulty": "easy", "leetcode_id": 1,
        "topics": ["arrays-hashing"],
        "canonical_solution": {
            "language": "python",
            "code": "def two_sum(n, t):\n    return [0, 1]\n",
            "time": "O(n)", "space": "O(n)",
        },
        "test_cases": [
            {"input": [[2, 7], 9], "expected": [0, 1]},
            {"input": [[1, 2], 3], "expected": [0, 1]},
            {"input": [[3, 3], 6], "expected": [0, 1]},
        ],
        "steps": [
            {"ordinal": i, "description": f"step {i} text here long enough", "pattern_tags": [], "hints": [
                {"level": 1, "text": f"hint level 1 step {i}"},
                {"level": 2, "text": f"hint level 2 step {i}"},
                {"level": 3, "text": f"hint level 3 step {i}"},
            ]} for i in range(1, 4)
        ],
    }
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(q))
    ingest_bank(conn, gen)


def test_get_hint_returns_text_for_current_step(db, tmp_path):
    _bootstrap_with_two_sum(db, tmp_path)
    out = get_next_question(db, slug="two-sum")
    sid = out["session_id"]
    fake = EvaluatorOutput(step_ordinal=2, correct=False, missing=["x"], suggested_move="nudge")
    with patch("whiteboard_mcp.tools.evaluate_attempt.evaluate", return_value=fake), \
         patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        evaluate_attempt(db, session_id=sid, user_text="...")

    h1 = get_hint(db, session_id=sid, level=1)
    assert h1 == {"level": 1, "text": "hint level 1 step 2", "step_ordinal": 2}
    h3 = get_hint(db, session_id=sid, level=3)
    assert h3["text"] == "hint level 3 step 2"


def test_get_hint_unknown_session(db):
    out = get_hint(db, session_id="nope", level=1)
    assert out["error"] == "not_found"


def test_get_hint_invalid_level(db, tmp_path):
    _bootstrap_with_two_sum(db, tmp_path)
    out = get_next_question(db, slug="two-sum")
    sid = out["session_id"]
    fake = EvaluatorOutput(step_ordinal=1, correct=False, missing=["x"], suggested_move="nudge")
    with patch("whiteboard_mcp.tools.evaluate_attempt.evaluate", return_value=fake), \
         patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        evaluate_attempt(db, session_id=sid, user_text="...")
    out = get_hint(db, session_id=sid, level=4)
    assert out["error"] == "invalid_level"


def test_get_hint_before_first_attempt(db, tmp_path):
    _bootstrap_with_two_sum(db, tmp_path)
    out = get_next_question(db, slug="two-sum")
    sid = out["session_id"]
    out = get_hint(db, session_id=sid, level=1)
    assert out["error"] == "no_current_step"
