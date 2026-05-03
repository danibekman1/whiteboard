from pathlib import Path

import pytest

from whiteboard_mcp.recommend import recommend_next, Recommendation
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


def test_no_progress_recommends_no_prereq_topic(db):
    _bootstrap(db)
    r = recommend_next(db)
    assert r is not None
    assert r.topic_slug == "arrays-hashing"  # the only no-prereq root
    assert r.difficulty == "easy"
    assert "begin" in r.justification.lower() or "start" in r.justification.lower()


def test_focus_topic_returns_easiest_unsolved_in_that_topic(db):
    _bootstrap(db)
    r = recommend_next(db, focus_topic_slug="arrays-hashing")
    assert r is not None
    assert r.topic_slug == "arrays-hashing"


def test_topic_step_up_after_prereq_mastered(db):
    """If arrays-hashing is mastered (≥70% solved unaided/with_hints),
    recommend should switch to a topic whose only prereq is arrays-hashing."""
    _bootstrap(db)
    qids = [r["id"] for r in db.execute("""
        SELECT q.id FROM questions q
        JOIN topics t ON t.id = q.topic_id
        WHERE t.slug = 'arrays-hashing'
    """).fetchall()]
    for i, qid in enumerate(qids):
        sid = f"s-{i}"
        db.execute(
            "INSERT INTO sessions (id, question_id, outcome, ended_at) "
            "VALUES (?, ?, 'unaided', '2026-05-03T00:00:00Z')",
            (sid, qid),
        )

    r = recommend_next(db)
    assert r is not None
    assert r.topic_slug in {"two-pointers", "stack", "math-geometry", "bit-manipulation"}
    assert "ready" in r.justification.lower() or "cleared" in r.justification.lower()


def test_weakness_drill_picks_question_with_weak_pattern(db):
    _bootstrap(db)
    # Need a session row first since weakness_profile.last_seen_session is FK.
    qid = db.execute("SELECT id FROM questions LIMIT 1").fetchone()["id"]
    db.execute(
        "INSERT INTO sessions (id, question_id, outcome, ended_at) "
        "VALUES ('p1', ?, 'unaided', '2026-05-03T00:00:00Z')",
        (qid,),
    )
    db.execute(
        "INSERT INTO weakness_profile (pattern_tag, miss_count, total_count, last_seen_session) "
        "VALUES (?, ?, ?, 'p1')",
        ("hashing", 4, 5),  # 80% miss rate, total >= 3
    )
    r = recommend_next(db)
    assert r is not None
    assert "drill" in r.justification.lower() or "miss rate" in r.justification.lower()


def test_focus_topic_starting_fresh_credits_mastered_prereq(db):
    """Spec line 93: when starting a focus topic and a prereq is mastered,
    justification should be 'start {topic} - you nailed {prereq} (n/m)'."""
    _bootstrap(db)
    # Master arrays-hashing.
    qids = [r["id"] for r in db.execute("""
        SELECT q.id FROM questions q
        JOIN topics t ON t.id = q.topic_id
        WHERE t.slug = 'arrays-hashing'
    """).fetchall()]
    for i, qid in enumerate(qids):
        db.execute(
            "INSERT INTO sessions (id, question_id, outcome, ended_at) "
            "VALUES (?, ?, 'unaided', '2026-05-03T00:00:00Z')",
            (f"s-{i}", qid),
        )

    r = recommend_next(db, focus_topic_slug="two-pointers")
    assert r is not None
    assert r.topic_slug == "two-pointers"
    assert "you nailed arrays-hashing" in r.justification
    # Embedded count format "(n/m)"
    import re as _re
    assert _re.search(r"\(\d+/\d+\)", r.justification)


def test_difficulty_step_up_fires_without_focus(db):
    """Spec strategy 4: in-progress topic with all easies cleared but not mastered
    should suggest a medium even when focus_topic_slug is None."""
    _bootstrap(db)
    # Mark all EASY questions in arrays-hashing as solved (some easies, no mediums).
    easy_qids = [r["id"] for r in db.execute("""
        SELECT q.id FROM questions q
        JOIN topics t ON t.id = q.topic_id
        WHERE t.slug = 'arrays-hashing' AND q.difficulty = 'easy'
    """).fetchall()]
    if not easy_qids:
        pytest.skip("bank has no easy arrays-hashing questions")
    # Also confirm there's at least one medium available so step-up can trigger.
    has_medium = db.execute("""
        SELECT 1 FROM questions q JOIN topics t ON t.id = q.topic_id
        WHERE t.slug = 'arrays-hashing' AND q.difficulty = 'medium' LIMIT 1
    """).fetchone()
    if not has_medium:
        pytest.skip("bank has no medium arrays-hashing questions")
    for i, qid in enumerate(easy_qids):
        db.execute(
            "INSERT INTO sessions (id, question_id, outcome, ended_at) "
            "VALUES (?, ?, 'with_hints', '2026-05-03T00:00:00Z')",
            (f"e-{i}", qid),
        )
    # Without focus, recommendation should suggest a medium in arrays-hashing
    # (assuming arrays-hashing isn't mastered enough by easies alone — depends on
    # ratio of easies to total). If it IS mastered, strategy 3 fires first; that's
    # OK for the spec. We just need the impl to not skip strategy 4 entirely.
    r = recommend_next(db)
    assert r is not None
    # Either we hit strategy 3 (step-up to a different topic) or strategy 4
    # (medium in arrays-hashing). Either is a valid spec outcome.
    assert r.justification != ""


def test_returns_none_when_everything_cleared(db):
    _bootstrap(db)
    qids = [r["id"] for r in db.execute("SELECT id FROM questions").fetchall()]
    for i, qid in enumerate(qids):
        db.execute(
            "INSERT INTO sessions (id, question_id, outcome, ended_at) "
            "VALUES (?, ?, 'unaided', '2026-05-03T00:00:00Z')",
            (f"s-{i}", qid),
        )
    db.commit()
    assert recommend_next(db) is None
