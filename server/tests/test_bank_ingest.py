import json
from pathlib import Path

import pytest

from whiteboard_mcp.db import connect, ensure_schema
from bank.ingest import ingest_bank
from bank.schemas import QuestionJSON


def _write_two_sum(out_dir: Path, slug: str = "two-sum"):
    q = {
        "slug": slug, "title": "Two Sum",
        "statement": "Given an array of integers, find pair summing to target.",
        "difficulty": "easy", "leetcode_id": 1,
        "topics": ["arrays-hashing", "hashing"],
        "canonical_solution": {
            "language": "python",
            "code": "def two_sum(nums, t):\n    return [0, 1]\n",
            "time": "O(n)", "space": "O(n)",
        },
        "test_cases": [
            {"input": [[2, 7], 9], "expected": [0, 1]},
            {"input": [[1, 2], 3], "expected": [0, 1]},
            {"input": [[3, 3], 6], "expected": [0, 1]},
        ],
        "steps": [
            {"ordinal": i, "description": f"step {i} description here", "pattern_tags": ["t"], "hints": [
                {"level": 1, "text": "h1"}, {"level": 2, "text": "h2"}, {"level": 3, "text": "h3"},
            ]} for i in range(1, 4)
        ],
    }
    QuestionJSON.model_validate(q)  # sanity
    (out_dir / f"{slug}.json").write_text(json.dumps(q))


def _seed_topics(conn):
    for slug, name in [("arrays-hashing", "Arrays & Hashing"), ("hashing", "Hashing")]:
        conn.execute("INSERT INTO topics (slug, name) VALUES (?, ?)", (slug, name))


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "coach.db"
    c = connect(db_path)
    ensure_schema(c)
    yield c
    c.close()


def test_ingest_writes_questions_steps_hints(conn, tmp_path):
    _seed_topics(conn)
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    _write_two_sum(gen_dir)

    n = ingest_bank(conn, gen_dir)
    assert n == 1

    q = conn.execute("SELECT * FROM questions WHERE slug='two-sum'").fetchone()
    assert q["leetcode_id"] == 1
    assert q["topic_id"] is not None  # primary topic set

    n_steps = conn.execute("SELECT COUNT(*) AS c FROM steps WHERE question_id=?", (q["id"],)).fetchone()["c"]
    assert n_steps == 3
    n_hints = conn.execute("""
        SELECT COUNT(*) AS c FROM hint_levels h
        JOIN steps s ON s.id = h.step_id WHERE s.question_id = ?
    """, (q["id"],)).fetchone()["c"]
    assert n_hints == 9  # 3 steps x 3 hints

    qt = conn.execute("SELECT COUNT(*) AS c FROM question_topics WHERE question_id=?", (q["id"],)).fetchone()["c"]
    assert qt == 2


def test_ingest_idempotent_replaces_steps_hints_topics(conn, tmp_path):
    _seed_topics(conn)
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    _write_two_sum(gen_dir)

    ingest_bank(conn, gen_dir)
    ingest_bank(conn, gen_dir)  # re-run: no dupes

    nq = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
    assert nq == 1
    nh = conn.execute("SELECT COUNT(*) AS c FROM hint_levels").fetchone()["c"]
    assert nh == 9


def test_ingest_skips_unknown_topic_with_warning(conn, tmp_path, capsys):
    # Note: NO topics seeded.
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    _write_two_sum(gen_dir)
    ingest_bank(conn, gen_dir)
    captured = capsys.readouterr()
    err = captured.err.lower()
    assert "unknown primary topic" in err and "arrays-hashing" in err
    # Secondary unknown topic surfaces as a single info summary line.
    assert "secondary topic" in err and "hashing" in err
    qt = conn.execute("SELECT COUNT(*) AS c FROM question_topics").fetchone()["c"]
    assert qt == 0
    # Question is still inserted but with topic_id=NULL (not silently dropped).
    q = conn.execute("SELECT topic_id FROM questions WHERE slug='two-sum'").fetchone()
    assert q is not None and q["topic_id"] is None


def test_ingest_skips_corrupt_json_file_and_continues(conn, tmp_path, capsys):
    """A corrupt or schema-invalid JSON in generated/ must be skipped with
    a stderr warning, not crash the whole ingest. Other valid files in the
    same directory must still be ingested."""
    _seed_topics(conn)
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    (gen_dir / "broken.json").write_text("{not valid json at all")
    _write_two_sum(gen_dir)

    n = ingest_bank(conn, gen_dir)
    assert n == 1  # only two-sum landed

    captured = capsys.readouterr()
    assert "skip broken.json" in captured.err.lower()
    nq = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
    assert nq == 1


def test_ingest_nulls_out_session_current_step_id_on_replace(conn, tmp_path):
    """Ingesting a bank update for a question that already has steps + an
    active session pointing to one of those steps must not be blocked by
    the sessions.current_step_id FK; the ingest sets the pointer to NULL."""
    _seed_topics(conn)
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    _write_two_sum(gen_dir)
    ingest_bank(conn, gen_dir)

    qid = conn.execute("SELECT id FROM questions WHERE slug='two-sum'").fetchone()["id"]
    sid = conn.execute("SELECT id FROM steps WHERE question_id=? AND ordinal=2", (qid,)).fetchone()["id"]
    conn.execute(
        "INSERT INTO sessions (id, question_id, current_step_id) VALUES (?,?,?)",
        ("s1", qid, sid),
    )
    conn.commit()

    # Re-ingest replaces steps; the session's stale step pointer must be
    # cleared, not block with FK constraint failure.
    ingest_bank(conn, gen_dir)

    row = conn.execute("SELECT current_step_id FROM sessions WHERE id='s1'").fetchone()
    assert row["current_step_id"] is None
