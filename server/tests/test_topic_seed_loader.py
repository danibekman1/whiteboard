import json
from pathlib import Path

from whiteboard_mcp.topic_seed_loader import ingest_topics, ingest_topic_prereqs

ROOT = Path(__file__).parent.parent
TOPICS = ROOT / "bank" / "seed" / "topics.json"
PREREQS = ROOT / "bank" / "seed" / "topic_prereqs.json"


def test_ingest_topics_inserts_all(db, tmp_path):
    seed = tmp_path / "topics.json"
    seed.write_text(json.dumps([
        {"slug": "arrays-hashing", "name": "Arrays & Hashing"},
        {"slug": "trees", "name": "Trees"},
    ]))
    n = ingest_topics(db, seed)
    assert n == 2
    rows = {r["slug"]: r["name"] for r in db.execute("SELECT slug, name FROM topics")}
    assert rows == {"arrays-hashing": "Arrays & Hashing", "trees": "Trees"}


def test_ingest_topics_idempotent_updates_name(db, tmp_path):
    seed = tmp_path / "topics.json"
    seed.write_text(json.dumps([{"slug": "trees", "name": "Trees"}]))
    ingest_topics(db, seed)
    seed.write_text(json.dumps([{"slug": "trees", "name": "Tree Patterns"}]))
    ingest_topics(db, seed)
    n = db.execute("SELECT COUNT(*) AS c FROM topics").fetchone()["c"]
    assert n == 1  # no dupe row
    name = db.execute("SELECT name FROM topics WHERE slug='trees'").fetchone()["name"]
    assert name == "Tree Patterns"


def test_ingest_topic_prereqs_writes_edges(db):
    ingest_topics(db, TOPICS)
    n = ingest_topic_prereqs(db, PREREQS)
    assert n == 17
    rows = db.execute("""
        SELECT t.slug AS topic, p.slug AS prereq FROM topic_prereqs e
        JOIN topics t ON t.id = e.topic_id
        JOIN topics p ON p.id = e.prereq_topic_id
    """).fetchall()
    edges = {(r["topic"], r["prereq"]) for r in rows}
    assert ("two-pointers", "arrays-hashing") in edges
    assert ("dp-2d", "dp-1d") in edges


def test_ingest_topic_prereqs_idempotent(db):
    ingest_topics(db, TOPICS)
    ingest_topic_prereqs(db, PREREQS)
    ingest_topic_prereqs(db, PREREQS)  # no error, no dupes
    n = db.execute("SELECT COUNT(*) AS c FROM topic_prereqs").fetchone()["c"]
    assert n == 17


def test_ingest_topic_prereqs_skips_unknown_with_warning(db, tmp_path, capsys):
    ingest_topics(db, TOPICS)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([
        {"topic": "two-pointers", "prereq": "arrays-hashing"},
        {"topic": "nope", "prereq": "arrays-hashing"},
    ]))
    n = ingest_topic_prereqs(db, bad)
    assert n == 1  # only the valid one landed
    cap = capsys.readouterr()
    err = (cap.out + cap.err).lower()
    assert "unknown topic" in err
    assert "'nope'" in err  # message names the missing slug, not just the dict


def test_ingest_topic_prereqs_rejects_cycle(db, tmp_path):
    """A 2-cycle (a -> b -> a) is not blocked by the schema CHECK constraint
    (which only catches self-loops). The loader must reject it explicitly."""
    import pytest
    seed = tmp_path / "topics.json"
    seed.write_text(json.dumps([
        {"slug": "a", "name": "A"},
        {"slug": "b", "name": "B"},
    ]))
    ingest_topics(db, seed)
    cyc = tmp_path / "cyc.json"
    cyc.write_text(json.dumps([
        {"topic": "b", "prereq": "a"},
        {"topic": "a", "prereq": "b"},
    ]))
    with pytest.raises(ValueError, match="cycle detected"):
        ingest_topic_prereqs(db, cyc)
