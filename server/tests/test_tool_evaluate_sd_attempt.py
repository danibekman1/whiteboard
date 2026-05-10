"""Tests for the evaluate_sd_attempt MCP tool.

Covers:
  - Happy path: SD session evaluates, attempt persisted with correct shape
  - Algo session rejected with wrong_question_type error
  - Unknown session returns not_found
  - Evaluator timeout returns evaluator_timeout
  - Evaluator parse failure returns evaluator_parse_failed
  - Internal error (catch-all) returns internal_error
  - session_so_far built correctly from prior attempts
"""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import anthropic
import pytest

from whiteboard_mcp.topic_seed_loader import ingest_topics
from whiteboard_mcp.tools.get_next_question import get_next_question
from whiteboard_mcp.tools.evaluate_sd_attempt import evaluate_sd_attempt
from whiteboard_mcp.sd_evaluator import SDEvaluatorOutput
from bank.ingest import ingest_bank


SEED = Path(__file__).parent.parent / "bank" / "seed"
CURATED = SEED / "sd_curated"


def _algo_q() -> dict:
    """Minimal algo question for type-rejection test."""
    return {
        "slug": "two-sum-test",
        "title": "Two Sum Test",
        "statement": "Given an array of integers nums and a target...",
        "difficulty": "easy",
        "leetcode_id": 1,
        "topics": ["arrays-hashing"],
        "canonical_solution": {"language": "python",
                               "code": "def two_sum(n,t): return [0,1]\n",
                               "time": "O(n)", "space": "O(n)"},
        "test_cases": [{"input": [[2, 7], 9], "expected": [0, 1]}] * 3,
        "steps": [{"ordinal": i,
                   "description": f"step {i} long enough description",
                   "pattern_tags": ["t"],
                   "hints": [{"level": 1, "text": "h1"},
                             {"level": 2, "text": "h2"},
                             {"level": 3, "text": "h3"}]}
                  for i in range(1, 4)],
    }


def _bootstrap_with_curated_sd(db, tmp_path):
    """Ingest topics + the real curated SD questions (using seed/sd_curated/
    so we exercise the production data path, not synthetic test fixtures)."""
    ingest_topics(db, SEED / "topics.json")
    ingest_bank(db, CURATED)


def _bootstrap_with_algo(db, tmp_path):
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum-test.json").write_text(json.dumps(_algo_q()))
    ingest_bank(db, gen)


def _mock_evaluator_output(**kwargs) -> SDEvaluatorOutput:
    return SDEvaluatorOutput(**{
        "phase": "clarify",
        "checklist_covered": [],
        "checklist_missing_required": [1],
        "pushback_triggered": None,
        "suggested_move": "press_on_missing",
        **kwargs,
    })


# --- happy path ------------------------------------------------------------

def test_evaluate_sd_attempt_happy_path(db, tmp_path):
    _bootstrap_with_curated_sd(db, tmp_path)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    fake = _mock_evaluator_output(phase="estimate", suggested_move="advance_phase")
    with patch("whiteboard_mcp.tools.evaluate_sd_attempt.evaluate", return_value=fake), \
         patch("whiteboard_mcp.tools.evaluate_sd_attempt.get_anthropic_client",
               return_value=MagicMock()):
        result = evaluate_sd_attempt(db, session_id=sid, user_text="100M URLs/year")

    assert result["phase"] == "estimate"
    assert result["suggested_move"] == "advance_phase"
    assert result["checklist_covered"] == []
    assert result["pushback_triggered"] is None

    # Attempt persisted.
    row = db.execute(
        "SELECT user_text, evaluator_json FROM attempts WHERE session_id=?", (sid,)
    ).fetchone()
    assert row["user_text"] == "100M URLs/year"
    assert json.loads(row["evaluator_json"])["phase"] == "estimate"


def test_evaluate_sd_attempt_passes_session_history_to_evaluator(db, tmp_path):
    """After multiple attempts, the evaluator should receive session_so_far
    populated with prior turns' phase + user_text."""
    _bootstrap_with_curated_sd(db, tmp_path)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    first = _mock_evaluator_output(phase="clarify", suggested_move="advance_phase")
    second = _mock_evaluator_output(phase="estimate", suggested_move="press_on_missing")
    captured_calls = []

    def fake_evaluate(*, session_so_far, **kwargs):
        captured_calls.append(session_so_far)
        # Return whichever is next in the queue.
        return [first, second][len(captured_calls) - 1]

    with patch("whiteboard_mcp.tools.evaluate_sd_attempt.evaluate", side_effect=fake_evaluate), \
         patch("whiteboard_mcp.tools.evaluate_sd_attempt.get_anthropic_client",
               return_value=MagicMock()):
        evaluate_sd_attempt(db, session_id=sid, user_text="users want fast redirects")
        evaluate_sd_attempt(db, session_id=sid, user_text="around 30 reads/sec")

    # First call: empty history.
    assert captured_calls[0] == []
    # Second call: history reflects what the FIRST evaluator returned, not a
    # hard-coded value (catches regressions where _load_session_so_far reads
    # from the wrong source but happens to produce a plausible phase).
    assert len(captured_calls[1]) == 1
    assert captured_calls[1][0]["phase"] == first.phase
    assert "fast redirects" in captured_calls[1][0]["user_text"]


# --- type rejection --------------------------------------------------------

def test_evaluate_sd_attempt_rejects_algo_session(db, tmp_path):
    _bootstrap_with_algo(db, tmp_path)
    sid = get_next_question(db, slug="two-sum-test")["session_id"]

    result = evaluate_sd_attempt(db, session_id=sid, user_text="anything")
    assert result == {
        "error": "wrong_question_type",
        "got": "algo",
        "expected": "system_design",
    }
    # No attempt persisted on rejection.
    n = db.execute("SELECT COUNT(*) AS c FROM attempts WHERE session_id=?", (sid,)).fetchone()["c"]
    assert n == 0


# --- not_found -------------------------------------------------------------

def test_evaluate_sd_attempt_unknown_session(db):
    result = evaluate_sd_attempt(db, session_id="nonexistent", user_text="anything")
    assert result["error"] == "not_found"
    assert result["entity"] == "session"
    assert result["value"] == "nonexistent"


# --- evaluator failure modes ----------------------------------------------

def test_evaluate_sd_attempt_timeout(db, tmp_path):
    _bootstrap_with_curated_sd(db, tmp_path)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    with patch("whiteboard_mcp.tools.evaluate_sd_attempt.evaluate",
               side_effect=anthropic.APITimeoutError(request=MagicMock())), \
         patch("whiteboard_mcp.tools.evaluate_sd_attempt.get_anthropic_client",
               return_value=MagicMock()):
        result = evaluate_sd_attempt(db, session_id=sid, user_text="anything")

    assert result == {"error": "evaluator_timeout"}
    n = db.execute("SELECT COUNT(*) AS c FROM attempts WHERE session_id=?", (sid,)).fetchone()["c"]
    assert n == 0  # nothing persisted on timeout


def test_evaluate_sd_attempt_parse_failure(db, tmp_path):
    _bootstrap_with_curated_sd(db, tmp_path)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    with patch("whiteboard_mcp.tools.evaluate_sd_attempt.evaluate",
               side_effect=ValueError("evaluator returned no tool_use block")), \
         patch("whiteboard_mcp.tools.evaluate_sd_attempt.get_anthropic_client",
               return_value=MagicMock()):
        result = evaluate_sd_attempt(db, session_id=sid, user_text="anything")

    assert result["error"] == "evaluator_parse_failed"
    assert result["raw"] == "evaluator returned no tool_use block"
    n = db.execute("SELECT COUNT(*) AS c FROM attempts WHERE session_id=?", (sid,)).fetchone()["c"]
    assert n == 0  # parse failure must not persist an attempt


def test_evaluate_sd_attempt_degrades_on_malformed_prior_evaluator_json(db, tmp_path):
    """If a prior attempt row has malformed evaluator_json, the next turn
    should still run and the rebuilt session_so_far should fall back to the
    DEFAULT_PHASE_FALLBACK for that entry. Pins the degradation contract in
    _load_session_so_far so a future refactor doesn't turn the json error
    into a 500."""
    _bootstrap_with_curated_sd(db, tmp_path)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    # Seed a malformed prior attempt directly (bypassing the tool).
    db.execute(
        "INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) "
        "VALUES (?,?,?,?)",
        (sid, 1, "earlier garbled turn", "{not valid json"),
    )
    db.commit()

    captured = []

    def fake_evaluate(*, session_so_far, **kwargs):
        captured.append(session_so_far)
        return _mock_evaluator_output(phase="estimate", suggested_move="advance_phase")

    with patch("whiteboard_mcp.tools.evaluate_sd_attempt.evaluate", side_effect=fake_evaluate), \
         patch("whiteboard_mcp.tools.evaluate_sd_attempt.get_anthropic_client",
               return_value=MagicMock()):
        result = evaluate_sd_attempt(db, session_id=sid, user_text="next turn")

    assert result["phase"] == "estimate"
    assert len(captured[0]) == 1
    # Fell back to the default phase rather than raising.
    assert captured[0][0]["phase"] == "clarify"
    assert captured[0][0]["user_text"] == "earlier garbled turn"


def test_evaluate_sd_attempt_internal_error(db, tmp_path):
    _bootstrap_with_curated_sd(db, tmp_path)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    with patch("whiteboard_mcp.tools.evaluate_sd_attempt.evaluate",
               side_effect=RuntimeError("network exploded")), \
         patch("whiteboard_mcp.tools.evaluate_sd_attempt.get_anthropic_client",
               return_value=MagicMock()):
        result = evaluate_sd_attempt(db, session_id=sid, user_text="anything")

    assert result["error"] == "internal_error"
    assert "network exploded" in result["message"]
    n = db.execute("SELECT COUNT(*) AS c FROM attempts WHERE session_id=?", (sid,)).fetchone()["c"]
    assert n == 0  # internal error must not persist a half-formed attempt
