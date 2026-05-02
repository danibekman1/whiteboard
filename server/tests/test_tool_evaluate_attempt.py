import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from whiteboard_mcp.evaluator import EvaluatorOutput
from whiteboard_mcp.seed_loader import ingest_seeds
from whiteboard_mcp.tools.evaluate_attempt import evaluate_attempt
from whiteboard_mcp.tools.get_next_question import get_next_question

SEED_DIR = Path(__file__).parent.parent / "whiteboard_mcp" / "seed"


def _start_two_sum_session(db) -> str:
    ingest_seeds(db, SEED_DIR)
    out = get_next_question(db, slug="two-sum")
    return out["session_id"]


def test_evaluate_attempt_persists_and_returns_assessment(db):
    sid = _start_two_sum_session(db)
    fake_eval = EvaluatorOutput(
        step_id=1, correct=True, missing=[], suggested_move="advance",
    )
    with patch("whiteboard_mcp.tools.evaluate_attempt.evaluate", return_value=fake_eval), \
         patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        out = evaluate_attempt(db, session_id=sid, user_text="brute force is O(n^2)")
    assert out["step_id"] == 1
    assert out["correct"] is True
    assert out["suggested_move"] == "advance"
    rows = db.execute(
        "SELECT * FROM attempts WHERE session_id = ? ORDER BY ordinal", (sid,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["user_text"] == "brute force is O(n^2)"
    assert json.loads(rows[0]["evaluator_json"])["step_id"] == 1


def test_evaluate_attempt_increments_ordinal(db):
    sid = _start_two_sum_session(db)
    fake_eval = EvaluatorOutput(
        step_id=1, correct=False, missing=["x"], suggested_move="nudge"
    )
    with patch("whiteboard_mcp.tools.evaluate_attempt.evaluate", return_value=fake_eval), \
         patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        evaluate_attempt(db, session_id=sid, user_text="a")
        evaluate_attempt(db, session_id=sid, user_text="b")
    rows = db.execute("SELECT ordinal FROM attempts WHERE session_id = ?", (sid,)).fetchall()
    assert [r["ordinal"] for r in rows] == [1, 2]


def test_evaluate_attempt_updates_current_step_id(db):
    sid = _start_two_sum_session(db)
    fake_eval = EvaluatorOutput(step_id=3, correct=True, missing=[], suggested_move="advance")
    with patch("whiteboard_mcp.tools.evaluate_attempt.evaluate", return_value=fake_eval), \
         patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        evaluate_attempt(db, session_id=sid, user_text="hash map gives O(1)")
    row = db.execute(
        "SELECT s.current_step_id, st.ordinal FROM sessions s "
        "LEFT JOIN steps st ON st.id = s.current_step_id WHERE s.id = ?",
        (sid,),
    ).fetchone()
    assert row["current_step_id"] is not None
    assert row["ordinal"] == 3


def test_evaluate_attempt_unknown_session_returns_error(db):
    out = evaluate_attempt(db, session_id="nope", user_text="hi")
    assert out["error"] == "not_found"
    assert out["entity"] == "session"


def test_evaluate_attempt_translates_evaluator_value_error(db):
    sid = _start_two_sum_session(db)
    with patch(
        "whiteboard_mcp.tools.evaluate_attempt.evaluate",
        side_effect=ValueError("evaluator returned no tool_use block"),
    ), patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        out = evaluate_attempt(db, session_id=sid, user_text="hi")
    assert out["error"] == "evaluator_parse_failed"
    assert "tool_use" in out["raw"]


def test_evaluate_attempt_translates_unexpected_exception(db):
    sid = _start_two_sum_session(db)
    with patch(
        "whiteboard_mcp.tools.evaluate_attempt.evaluate",
        side_effect=RuntimeError("network down"),
    ), patch("whiteboard_mcp.tools.evaluate_attempt.get_anthropic_client", return_value=MagicMock()):
        out = evaluate_attempt(db, session_id=sid, user_text="hi")
    assert out["error"] == "internal_error"
    assert "network down" in out["message"]
