"""SD-specific cases for get_session.

Layered on top of test_tool_get_session.py (which covers the algo path);
asserts SD sessions return type, scenario_tag, pushbacks, and current_phase.
Algo cases here also lock in that the new keys behave correctly for algo
sessions (type='algo', current_phase=null, no scenario_tag/pushbacks)."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from whiteboard_mcp.topic_seed_loader import ingest_topics
from whiteboard_mcp.tools.get_next_question import get_next_question
from whiteboard_mcp.tools.get_session import get_session
from whiteboard_mcp.tools.evaluate_sd_attempt import evaluate_sd_attempt
from whiteboard_mcp.sd_evaluator import SDEvaluatorOutput
from bank.ingest import ingest_bank


SEED = Path(__file__).parent.parent / "bank" / "seed"
CURATED = SEED / "sd_curated"


def _bootstrap_curated(db):
    ingest_topics(db, SEED / "topics.json")
    ingest_bank(db, CURATED)


def test_get_session_sd_returns_type_and_scenario_tag(db, tmp_path):
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]
    s = get_session(db, session_id=sid)
    assert s["question"]["type"] == "system_design"
    assert s["question"]["scenario_tag"] == "high read traffic"


def test_get_session_sd_returns_pushbacks(db, tmp_path):
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]
    s = get_session(db, session_id=sid)
    assert "pushbacks" in s
    # url-shortener has exactly 5 pushbacks per the curated content.
    # Pinning the count catches both regressions that drop rows and
    # accidental duplicate inserts.
    assert len(s["pushbacks"]) == 5
    pb = s["pushbacks"][0]
    assert {"trigger_tag", "trigger_desc", "response"} <= set(pb.keys())
    # Anchor at least one trigger_tag + response pair to the curated source
    # so an empty response or shuffled rows are caught.
    by_tag = {p["trigger_tag"]: p for p in s["pushbacks"]}
    assert "no_capacity_estimate" in by_tag
    assert by_tag["no_capacity_estimate"]["response"].startswith(
        "Hold on - we don't know yet"
    )


def test_get_session_sd_current_phase_null_before_first_attempt(db, tmp_path):
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]
    s = get_session(db, session_id=sid)
    assert s["current_phase"] is None


def test_get_session_sd_current_phase_derived_from_latest_attempt(db, tmp_path):
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    # Mock two evaluator outputs; second wins for current_phase.
    first = SDEvaluatorOutput(phase="clarify", suggested_move="advance_phase")
    second = SDEvaluatorOutput(phase="estimate", suggested_move="press_on_missing")
    outputs = iter([first, second])
    with patch("whiteboard_mcp.tools.evaluate_sd_attempt.evaluate",
               side_effect=lambda **_: next(outputs)), \
         patch("whiteboard_mcp.tools.evaluate_sd_attempt.get_anthropic_client",
               return_value=MagicMock()):
        evaluate_sd_attempt(db, session_id=sid, user_text="who are the users?")
        evaluate_sd_attempt(db, session_id=sid, user_text="around 30 reads/sec")

    s = get_session(db, session_id=sid)
    assert s["current_phase"] is not None
    assert s["current_phase"]["phase"] == "estimate"
    assert s["current_phase"]["ordinal"] == 2


def test_get_session_sd_handles_malformed_evaluator_json_gracefully(db, tmp_path):
    """If a prior attempt has malformed evaluator_json (shouldn't happen but
    defense-in-depth), current_phase falls back to null rather than crashing."""
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]
    db.execute(
        "INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) "
        "VALUES (?, 1, 'x', 'not json')",
        (sid,),
    )
    db.commit()
    s = get_session(db, session_id=sid)
    # Either null current_phase or a default like 'clarify' is acceptable -
    # the contract is "no crash". Implementation choice: return null on parse
    # failure (clearer signal than fake-default).
    assert s["current_phase"] is None


def test_get_session_sd_handles_unknown_phase_string_gracefully(db, tmp_path):
    """Valid JSON whose `phase` is a string not in the known phase set
    (e.g. an evaluator schema drift) -> current_phase falls back to null
    rather than guessing an ordinal."""
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]
    db.execute(
        "INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) "
        "VALUES (?, 1, 'x', ?)",
        (sid, '{"phase": "settle", "suggested_move": "nudge"}'),
    )
    db.commit()
    s = get_session(db, session_id=sid)
    assert s["current_phase"] is None


def test_get_session_sd_scenario_tag_always_present_for_sd(db, tmp_path):
    """Spec §3: scenario_tag is 'SD only; null for algo'. Implementation:
    always-present (value or null) for SD, omitted for algo."""
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]
    s = get_session(db, session_id=sid)
    assert "scenario_tag" in s["question"]
    assert s["question"]["scenario_tag"] == "high read traffic"


# --- algo-side regressions ------------------------------------------------

def _algo_q() -> dict:
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


def test_get_session_algo_has_type_algo_and_no_sd_keys(db, tmp_path):
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum-test.json").write_text(json.dumps(_algo_q()))
    ingest_bank(db, gen)

    sid = get_next_question(db, slug="two-sum-test")["session_id"]
    s = get_session(db, session_id=sid)
    assert s["question"]["type"] == "algo"
    assert "scenario_tag" not in s["question"]
    assert "pushbacks" not in s
    assert s["current_phase"] is None


def test_get_session_unknown_returns_not_found_unchanged(db):
    """Pre-PR-4 contract preserved: unknown session id returns not_found."""
    s = get_session(db, session_id="nonexistent")
    assert s["error"] == "not_found"
