from pathlib import Path

from whiteboard_mcp.seed_loader import ingest_seeds
from whiteboard_mcp.tools.get_next_question import get_next_question

SEED_DIR = Path(__file__).parent.parent / "whiteboard_mcp" / "seed"


def test_returns_session_with_question(db):
    ingest_seeds(db, SEED_DIR)
    out = get_next_question(db, slug="two-sum")
    assert "session_id" in out
    assert out["question"]["slug"] == "two-sum"
    assert out["question"]["title"] == "Two Sum"
    assert "Given an array" in out["question"]["statement"]
    # Crucial: canonical steps NEVER returned to caller.
    assert "steps" not in out["question"]
    assert "canonical" not in str(out).lower()


def test_creates_session_row(db):
    ingest_seeds(db, SEED_DIR)
    out = get_next_question(db, slug="two-sum")
    sid = out["session_id"]
    row = db.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    assert row is not None
    assert row["current_step_id"] is None  # nothing attempted yet


def test_random_when_no_slug(db):
    ingest_seeds(db, SEED_DIR)
    out = get_next_question(db)
    assert out["question"]["slug"] in {
        "two-sum",
        "valid-parentheses",
        "reverse-linked-list",
        "binary-search",
        "climbing-stairs",
    }


def test_unknown_slug_returns_error(db):
    ingest_seeds(db, SEED_DIR)
    out = get_next_question(db, slug="nope")
    assert out["error"] == "not_found"
    assert out["entity"] == "question"
    assert out["value"] == "nope"


def test_empty_bank_returns_error(db):
    out = get_next_question(db)
    assert out == {
        "error": "not_found",
        "entity": "question",
        "by": "*",
        "value": "(empty bank)",
    }
