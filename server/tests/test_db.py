import sqlite3

import pytest


def test_schema_creates_expected_tables(db):
    # sqlite_sequence is auto-created for AUTOINCREMENT columns; filter it.
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert names == {
        "questions", "steps", "sessions", "attempts",
        "topics", "question_topics", "hint_levels",
    }


def test_foreign_keys_pragma_is_enforced(db):
    # Insert a step with a bogus question_id; the PRAGMA must reject it.
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO steps (question_id, ordinal, description, pattern_tags) "
            "VALUES (?,?,?,?)",
            (9999, 1, "x", "[]"),
        )


def test_questions_unique_slug(db):
    db.execute(
        "INSERT INTO questions (slug, title, statement, difficulty) VALUES (?,?,?,?)",
        ("two-sum", "Two Sum", "...", "easy"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO questions (slug, title, statement, difficulty) VALUES (?,?,?,?)",
            ("two-sum", "Two Sum", "...", "easy"),
        )


def test_attempts_unique_ordinal_per_session(db):
    db.execute(
        "INSERT INTO questions (slug, title, statement, difficulty) VALUES (?,?,?,?)",
        ("two-sum", "Two Sum", "...", "easy"),
    )
    qid = db.execute("SELECT id FROM questions WHERE slug='two-sum'").fetchone()["id"]
    db.execute("INSERT INTO sessions (id, question_id) VALUES (?, ?)", ("s1", qid))
    db.execute(
        "INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) VALUES (?,?,?,?)",
        ("s1", 1, "hi", "{}"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) VALUES (?,?,?,?)",
            ("s1", 1, "again", "{}"),
        )


def test_topics_table_exists(db):
    db.execute("INSERT INTO topics (slug, name) VALUES (?, ?)", ("arrays-hashing", "Arrays & Hashing"))
    row = db.execute("SELECT slug FROM topics").fetchone()
    assert row["slug"] == "arrays-hashing"


def test_question_topics_many_to_many(db):
    db.execute("INSERT INTO topics (slug, name) VALUES (?, ?)", ("arrays-hashing", "Arrays & Hashing"))
    db.execute("INSERT INTO topics (slug, name) VALUES (?, ?)", ("hashing", "Hashing"))
    db.execute(
        "INSERT INTO questions (slug, title, statement, difficulty) VALUES (?,?,?,?)",
        ("two-sum", "Two Sum", "...", "easy"),
    )
    qid = db.execute("SELECT id FROM questions WHERE slug='two-sum'").fetchone()["id"]
    t1 = db.execute("SELECT id FROM topics WHERE slug='arrays-hashing'").fetchone()["id"]
    t2 = db.execute("SELECT id FROM topics WHERE slug='hashing'").fetchone()["id"]
    db.execute(
        "INSERT INTO question_topics (question_id, topic_id, is_primary) VALUES (?,?,1)", (qid, t1)
    )
    db.execute(
        "INSERT INTO question_topics (question_id, topic_id, is_primary) VALUES (?,?,0)", (qid, t2)
    )
    n = db.execute("SELECT COUNT(*) AS c FROM question_topics WHERE question_id=?", (qid,)).fetchone()["c"]
    assert n == 2


def test_hint_levels_unique_per_step(db):
    db.execute(
        "INSERT INTO questions (slug, title, statement, difficulty) VALUES (?,?,?,?)",
        ("two-sum", "Two Sum", "...", "easy"),
    )
    qid = db.execute("SELECT id FROM questions WHERE slug='two-sum'").fetchone()["id"]
    db.execute(
        "INSERT INTO steps (question_id, ordinal, description, pattern_tags) VALUES (?,?,?,?)",
        (qid, 1, "...", "[]"),
    )
    sid = db.execute("SELECT id FROM steps WHERE question_id=?", (qid,)).fetchone()["id"]
    db.execute("INSERT INTO hint_levels (step_id, level, text) VALUES (?,?,?)", (sid, 1, "h1"))
    db.execute("INSERT INTO hint_levels (step_id, level, text) VALUES (?,?,?)", (sid, 2, "h2"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO hint_levels (step_id, level, text) VALUES (?,?,?)", (sid, 1, "dup"))


def test_hint_level_constraint(db):
    db.execute(
        "INSERT INTO questions (slug, title, statement, difficulty) VALUES (?,?,?,?)",
        ("two-sum", "Two Sum", "...", "easy"),
    )
    qid = db.execute("SELECT id FROM questions WHERE slug='two-sum'").fetchone()["id"]
    db.execute(
        "INSERT INTO steps (question_id, ordinal, description, pattern_tags) VALUES (?,?,?,?)",
        (qid, 1, "...", "[]"),
    )
    sid = db.execute("SELECT id FROM steps WHERE question_id=?", (qid,)).fetchone()["id"]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO hint_levels (step_id, level, text) VALUES (?,?,?)", (sid, 4, "out of range"))


def test_questions_has_leetcode_id_and_topic_id(db):
    cols = {r["name"] for r in db.execute("PRAGMA table_info(questions)").fetchall()}
    assert "leetcode_id" in cols
    assert "topic_id" in cols


def test_ensure_schema_idempotent_on_v0_db(tmp_path):
    """Migration helper must handle a v0-shape DB (questions without leetcode_id/topic_id)."""
    from whiteboard_mcp.db import connect, ensure_schema
    db_path = tmp_path / "coach.db"
    raw = sqlite3.connect(str(db_path))
    raw.executescript("""
      CREATE TABLE questions (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL, statement TEXT NOT NULL, difficulty TEXT NOT NULL);
      CREATE TABLE steps (id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER NOT NULL,
        ordinal INTEGER NOT NULL, description TEXT NOT NULL, pattern_tags TEXT NOT NULL,
        UNIQUE(question_id, ordinal));
    """)
    raw.commit()
    raw.close()

    conn = connect(db_path)
    ensure_schema(conn)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
    assert "leetcode_id" in cols and "topic_id" in cols
    ensure_schema(conn)
    conn.close()
