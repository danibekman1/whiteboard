import json
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from whiteboard_mcp.db import VALID_OUTCOMES
from whiteboard_mcp.topic_seed_loader import ingest_topics, ingest_topic_prereqs
from bank.ingest import ingest_bank
from whiteboard_mcp.tools.get_next_question import get_next_question
from whiteboard_mcp.tools.evaluate_attempt import evaluate_attempt
from whiteboard_mcp.tools.record_outcome import record_outcome
from whiteboard_mcp.evaluator import EvaluatorOutput

ROOT = Path(__file__).parent.parent
TOPICS = ROOT / "bank" / "seed" / "topics.json"
PREREQS = ROOT / "bank" / "seed" / "topic_prereqs.json"


def _bootstrap(db, tmp_path):
    ingest_topics(db, TOPICS)
    ingest_topic_prereqs(db, PREREQS)
    q = {
        "slug": "two-sum", "title": "Two Sum",
        "statement": "Given an array of integers nums and a target, return indices summing to target.",
        "difficulty": "easy", "leetcode_id": 1, "topics": ["arrays-hashing"],
        "canonical_solution": {
            "language": "python",
            "code": "def two_sum(n,t):\n    return [0,1]\n",
            "time": "O(n)", "space": "O(n)",
        },
        "test_cases": [
            {"input": [[2, 7], 9], "expected": [0, 1]},
            {"input": [[1, 2], 3], "expected": [0, 1]},
            {"input": [[3, 3], 6], "expected": [0, 1]},
        ],
        "steps": [
            {"ordinal": 1, "description": "Step 1: a Socratic thought about the problem.",
             "pattern_tags": ["complexity-analysis"], "hints": [
                 {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"}]},
            {"ordinal": 2, "description": "Step 2: a Socratic thought about the problem.",
             "pattern_tags": ["hashing"], "hints": [
                 {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"}]},
            {"ordinal": 3, "description": "Step 3: a Socratic thought about the problem.",
             "pattern_tags": ["edge-cases"], "hints": [
                 {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"}]},
        ],
    }
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(q))
    ingest_bank(db, gen)


def _attempt(db, sid, step_ordinal, correct, suggested_move="nudge"):
    fake = EvaluatorOutput(
        step_ordinal=step_ordinal, correct=correct,
        missing=[] if correct else ["x"], suggested_move=suggested_move,
    )
    with patch("whiteboard_mcp.tools.evaluate_attempt.evaluate", return_value=fake), \
         patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        evaluate_attempt(db, session_id=sid, user_text="...")


def test_record_outcome_writes_session_state(db, tmp_path):
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    _attempt(db, sid, 1, True)
    out = record_outcome(db, session_id=sid, outcome="unaided", hints_used=[])
    assert out["ok"] is True
    row = db.execute(
        "SELECT outcome, ended_at, hints_used_json FROM sessions WHERE id=?", (sid,)
    ).fetchone()
    assert row["outcome"] == "unaided"
    assert row["ended_at"] is not None
    assert json.loads(row["hints_used_json"]) == []


def test_record_outcome_bumps_weakness_for_missed_pattern_tags(db, tmp_path):
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    # User missed step 1 once, then nailed; missed step 2 once, then nailed; nailed step 3 first try.
    _attempt(db, sid, 1, False)
    _attempt(db, sid, 1, True)
    _attempt(db, sid, 2, False)
    _attempt(db, sid, 2, True)
    _attempt(db, sid, 3, True)
    out = record_outcome(
        db, session_id=sid, outcome="with_hints",
        hints_used=[{"step_ordinal": 2, "level": 1}],
    )
    by_tag = {u["pattern_tag"]: u for u in out["weakness_updates"]}
    assert by_tag["complexity-analysis"]["miss_count"] == 1
    assert by_tag["complexity-analysis"]["total_count"] == 1
    assert by_tag["hashing"]["miss_count"] == 1
    assert by_tag["hashing"]["total_count"] == 1
    # Edge-cases nailed first try -> 0/1.
    assert by_tag["edge-cases"]["miss_count"] == 0
    assert by_tag["edge-cases"]["total_count"] == 1


def test_record_outcome_unknown_session(db):
    out = record_outcome(db, session_id="nope", outcome="unaided", hints_used=[])
    assert out["error"] == "not_found"


def test_record_outcome_invalid_outcome(db, tmp_path):
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    _attempt(db, sid, 1, True)
    out = record_outcome(db, session_id=sid, outcome="bogus", hints_used=[])
    assert out["error"] == "invalid_outcome"


def test_record_outcome_idempotent_does_not_double_bump(db, tmp_path):
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    _attempt(db, sid, 1, False)
    _attempt(db, sid, 1, True)
    record_outcome(db, session_id=sid, outcome="with_hints", hints_used=[])
    record_outcome(db, session_id=sid, outcome="with_hints", hints_used=[])  # second call
    row = db.execute(
        "SELECT miss_count, total_count FROM weakness_profile WHERE pattern_tag='complexity-analysis'"
    ).fetchone()
    assert row["miss_count"] == 1 and row["total_count"] == 1  # NOT 2/2


@pytest.mark.parametrize("outcome", VALID_OUTCOMES)
def test_record_outcome_accepts_every_valid_outcome(db, tmp_path, outcome):
    """Pin Python tuple ↔ SQLite CHECK constraint in lockstep across all outcomes."""
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    _attempt(db, sid, 1, True)
    out = record_outcome(db, session_id=sid, outcome=outcome, hints_used=[])
    assert out["ok"] is True
    row = db.execute("SELECT outcome FROM sessions WHERE id=?", (sid,)).fetchone()
    assert row["outcome"] == outcome


def test_record_outcome_zero_attempts_no_weakness_updates(db, tmp_path):
    """A skipped session with no attempts: outcome is recorded, weakness untouched."""
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    out = record_outcome(db, session_id=sid, outcome="skipped", hints_used=[])
    assert out["ok"] is True
    assert out["weakness_updates"] == []
    n = db.execute("SELECT COUNT(*) AS c FROM weakness_profile").fetchone()["c"]
    assert n == 0


def test_record_outcome_writes_iso_timestamp(db, tmp_path):
    """ended_at is the strftime('%Y-%m-%dT%H:%M:%fZ','now') format, not a literal."""
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    _attempt(db, sid, 1, True)
    record_outcome(db, session_id=sid, outcome="unaided", hints_used=[])
    row = db.execute("SELECT ended_at FROM sessions WHERE id=?", (sid,)).fetchone()
    # Format: 2026-05-03T16:25:00.123Z
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", row["ended_at"])


def test_record_outcome_silently_drops_out_of_range_step_ordinal(db, tmp_path):
    """If evaluate_attempt persisted an attempt with a step_ordinal that doesn't
    exist in the steps table, record_outcome should still succeed (no crash) and
    just skip that attempt's pattern_tags. Documents the silent-drop behaviour."""
    _bootstrap(db, tmp_path)
    sid = get_next_question(db, slug="two-sum")["session_id"]
    # Inject a bogus attempt with step_ordinal=99 (out of range).
    bogus = json.dumps({"step_ordinal": 99, "correct": False, "missing": ["x"], "suggested_move": "nudge"})
    db.execute(
        "INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) VALUES (?, ?, ?, ?)",
        (sid, 1, "...", bogus),
    )
    out = record_outcome(db, session_id=sid, outcome="partial", hints_used=[])
    assert out["ok"] is True
    assert out["weakness_updates"] == []  # bogus ordinal -> no tags found
