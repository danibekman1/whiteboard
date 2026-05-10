"""get_hint must reject SD sessions cleanly with not_supported_for_sd.

SD coaching is driven by pushbacks and Socratic phase advancement, not
graded hints. The outer coach prompt (PR 5) tells the model not to call
get_hint on SD sessions, but the server enforces it as well."""
from __future__ import annotations
from pathlib import Path

from whiteboard_mcp.topic_seed_loader import ingest_topics
from whiteboard_mcp.tools.get_next_question import get_next_question
from whiteboard_mcp.tools.get_hint import get_hint
from bank.ingest import ingest_bank


SEED = Path(__file__).parent.parent / "bank" / "seed"
CURATED = SEED / "sd_curated"


def test_get_hint_on_sd_session_returns_not_supported(db):
    ingest_topics(db, SEED / "topics.json")
    ingest_bank(db, CURATED)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    result = get_hint(db, session_id=sid, level=1)
    assert result == {
        "error": "not_supported_for_sd",
        "tool": "get_hint",
        "message": "get_hint is not supported for system_design sessions",
    }


def test_get_hint_on_sd_session_rejects_before_validating_level(db):
    """Type rejection should fire before level validation - the user got the
    wrong tool, not the wrong arguments."""
    ingest_topics(db, SEED / "topics.json")
    ingest_bank(db, CURATED)
    sid = get_next_question(db, slug="url-shortener")["session_id"]

    result = get_hint(db, session_id=sid, level=99)  # invalid level
    # Expect not_supported_for_sd, NOT invalid_level - the type mismatch is
    # the more useful error to surface.
    assert result["error"] == "not_supported_for_sd"
