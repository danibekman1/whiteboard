import json
from whiteboard_mcp.topic_seed_loader import ingest_topics


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
