import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from whiteboard_mcp.topic_seed_loader import ingest_topics
from bank.ingest import ingest_bank
from whiteboard_mcp.tools.get_next_question import get_next_question
from whiteboard_mcp.tools.evaluate_attempt import evaluate_attempt
from whiteboard_mcp.tools.get_session import get_session
from whiteboard_mcp.evaluator import EvaluatorOutput

ROOT = Path(__file__).parent.parent
TOPICS = ROOT / "bank" / "seed" / "topics.json"


def _bootstrap(db, tmp_path):
    ingest_topics(db, TOPICS)
    q = {
        "slug": "two-sum", "title": "Two Sum",
        "statement": "Given an array of integers nums and a target...",
        "difficulty": "easy", "leetcode_id": 1, "topics": ["arrays-hashing"],
        "canonical_solution": {"language": "python", "code": "def two_sum(n,t): return [0,1]\n", "time": "O(n)", "space": "O(n)"},
        "test_cases": [{"input": [[2,7], 9], "expected": [0,1]}] * 3,
        "steps": [
            {"ordinal": i, "description": f"step {i} description text", "pattern_tags": ["t"], "hints": [
                {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"}]} for i in range(1, 4)
        ],
    }
    gen = tmp_path / "gen"; gen.mkdir(); (gen / "two-sum.json").write_text(json.dumps(q))
    ingest_bank(db, gen)


def test_get_session_returns_question_metadata(db, tmp_path):
    _bootstrap(db, tmp_path)
    out = get_next_question(db, slug="two-sum")
    sid = out["session_id"]

    s = get_session(db, session_id=sid)
    assert s["session_id"] == sid
    assert s["question"]["slug"] == "two-sum"
    assert s["question"]["title"] == "Two Sum"
    assert "Given an array" in s["question"]["statement"]
    assert s["question"]["difficulty"] == "easy"
    assert s["current_step_ordinal"] is None  # no attempts yet
    assert s["attempts_count"] == 0
    assert s["outcome"] is None


def test_get_session_never_returns_canonical_steps(db, tmp_path):
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    s = get_session(db, session_id=sid)
    # Belt-and-suspenders: the entire payload as JSON must not contain step descriptions.
    payload = json.dumps(s)
    assert "step 1 description" not in payload
    assert "canonical" not in payload.lower()


def test_get_session_reflects_current_step_after_attempts(db, tmp_path):
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    fake = EvaluatorOutput(step_ordinal=2, correct=False, missing=["x"], suggested_move="nudge")
    with patch("whiteboard_mcp.tools.evaluate_attempt.evaluate", return_value=fake), \
         patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        evaluate_attempt(db, session_id=sid, user_text="...")
        evaluate_attempt(db, session_id=sid, user_text="...")
    s = get_session(db, session_id=sid)
    assert s["current_step_ordinal"] == 2
    assert s["attempts_count"] == 2


def test_get_session_unknown_returns_error(db):
    out = get_session(db, session_id="nope")
    assert out["error"] == "not_found"
