"""SD-specific cases for get_roadmap.

Asserts:
  - sd_questions[] returned with {slug, title, difficulty, scenario_tag, latest_outcome}
  - questions[] (algo) excludes SD rows
  - latest_outcome reflects most recent ended SD session per slug
  - existing topics[]/edges[]/recommendation/weakness shape unchanged"""
from __future__ import annotations
from pathlib import Path

from whiteboard_mcp.topic_seed_loader import ingest_topics, ingest_topic_prereqs
from whiteboard_mcp.tools.get_roadmap import get_roadmap
from whiteboard_mcp.tools.get_next_question import get_next_question
from whiteboard_mcp.tools.record_outcome import record_outcome
from bank.ingest import ingest_bank


SEED = Path(__file__).parent.parent / "bank" / "seed"
CURATED = SEED / "sd_curated"


def _bootstrap_curated(db):
    ingest_topics(db, SEED / "topics.json")
    ingest_topic_prereqs(db, SEED / "topic_prereqs.json")
    ingest_bank(db, CURATED)


def test_get_roadmap_returns_sd_questions(db):
    _bootstrap_curated(db)
    rm = get_roadmap(db)
    assert "sd_questions" in rm
    slugs = {q["slug"] for q in rm["sd_questions"]}
    assert {"url-shortener", "parking-lot", "rate-limiter"} <= slugs


def test_sd_question_row_shape(db):
    _bootstrap_curated(db)
    rm = get_roadmap(db)
    by_slug = {q["slug"]: q for q in rm["sd_questions"]}
    url = by_slug["url-shortener"]
    assert url["title"] == "URL Shortener"
    assert url["difficulty"] == "medium"
    assert url["scenario_tag"] == "high read traffic"
    assert url["latest_outcome"] is None


def test_sd_questions_excluded_from_algo_questions_list(db):
    _bootstrap_curated(db)
    rm = get_roadmap(db)
    algo_slugs = {q["slug"] for q in rm["questions"]}
    sd_slugs = {q["slug"] for q in rm["sd_questions"]}
    assert algo_slugs.isdisjoint(sd_slugs)
    # SD slugs should NOT appear in the algo array.
    assert "url-shortener" not in algo_slugs


def test_sd_question_latest_outcome_reflects_most_recent_session(db):
    _bootstrap_curated(db)
    sid = get_next_question(db, slug="url-shortener")["session_id"]
    record_outcome(db, session_id=sid, outcome="unaided", hints_used=[])

    rm = get_roadmap(db)
    by_slug = {q["slug"]: q for q in rm["sd_questions"]}
    assert by_slug["url-shortener"]["latest_outcome"] == "unaided"
    # Untouched ones still null.
    assert by_slug["parking-lot"]["latest_outcome"] is None


def test_existing_roadmap_keys_unchanged(db):
    _bootstrap_curated(db)
    rm = get_roadmap(db)
    # Pre-PR-4 keys must all still be present.
    for key in ("topics", "edges", "questions", "recommendation", "weakness"):
        assert key in rm, f"missing pre-existing key {key}"


def test_sd_questions_sorted_by_difficulty_then_slug(db):
    """UI groups by difficulty (easy/medium/hard); list should arrive sorted
    so the client doesn't need to re-sort."""
    _bootstrap_curated(db)
    rm = get_roadmap(db)
    diffs = [(q["difficulty"], q["slug"]) for q in rm["sd_questions"]]
    diff_order = {"easy": 0, "medium": 1, "hard": 2}
    expected = sorted(diffs, key=lambda x: (diff_order[x[0]], x[1]))
    assert diffs == expected
