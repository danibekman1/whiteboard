from pathlib import Path

import pytest

from whiteboard_mcp.tools.get_roadmap import get_roadmap
from whiteboard_mcp.topic_seed_loader import ingest_topics, ingest_topic_prereqs
from bank.ingest import ingest_bank

ROOT = Path(__file__).parent.parent
TOPICS = ROOT / "bank" / "seed" / "topics.json"
PREREQS = ROOT / "bank" / "seed" / "topic_prereqs.json"
GENERATED = ROOT / "bank" / "generated"


def _bootstrap(db):
    ingest_topics(db, TOPICS)
    ingest_topic_prereqs(db, PREREQS)
    if GENERATED.exists():
        ingest_bank(db, GENERATED)


def _has_bank() -> bool:
    return GENERATED.exists() and any(GENERATED.iterdir())


pytestmark = pytest.mark.skipif(not _has_bank(), reason="bank/generated/ not populated")


def test_returns_topics_with_status_and_edges(db):
    _bootstrap(db)
    out = get_roadmap(db)
    assert "topics" in out and "edges" in out and "questions" in out and "recommendation" in out
    by_slug = {t["slug"]: t for t in out["topics"]}
    # arrays-hashing: no prereqs and no progress -> 'unlocked'
    assert by_slug["arrays-hashing"]["status"] == "unlocked"
    # two-pointers: arrays-hashing prereq, not mastered -> 'locked'
    assert by_slug["two-pointers"]["status"] == "locked"
    # edge present
    assert {"from": "arrays-hashing", "to": "two-pointers"} in out["edges"]


def test_question_status_reflects_latest_session(db):
    _bootstrap(db)
    qid = db.execute("SELECT id FROM questions WHERE slug='two-sum'").fetchone()["id"]
    db.execute(
        "INSERT INTO sessions (id, question_id, outcome, ended_at) "
        "VALUES ('s1', ?, 'unaided', '2026-05-03T00:00:00Z')",
        (qid,),
    )
    out = get_roadmap(db)
    by_slug = {q["slug"]: q for q in out["questions"]}
    assert by_slug["two-sum"]["status"] == "unaided"


def test_focus_topic_changes_recommendation(db):
    _bootstrap(db)
    out = get_roadmap(db, focus_topic_slug="arrays-hashing")
    assert out["recommendation"] is not None
    assert out["recommendation"]["topic_slug"] == "arrays-hashing"


def test_weakness_top_five(db):
    _bootstrap(db)
    # Need a session row for the FK on weakness_profile.last_seen_session.
    qid = db.execute("SELECT id FROM questions LIMIT 1").fetchone()["id"]
    db.execute(
        "INSERT INTO sessions (id, question_id, outcome, ended_at) "
        "VALUES ('s0', ?, 'unaided', '2026-05-03T00:00:00Z')",
        (qid,),
    )
    for i in range(7):
        db.execute(
            "INSERT INTO weakness_profile (pattern_tag, miss_count, total_count, last_seen_session) "
            "VALUES (?, ?, ?, 's0')",
            (f"p{i}", i, 10),
        )
    out = get_roadmap(db)
    assert len(out["weakness"]) == 5
    rates = [w["miss_rate"] for w in out["weakness"]]
    assert rates == sorted(rates, reverse=True)
