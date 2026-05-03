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
        "topic_prereqs", "weakness_profile",
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


def test_topic_prereqs_table(db):
    db.execute("INSERT INTO topics (slug, name) VALUES ('a','A')")
    db.execute("INSERT INTO topics (slug, name) VALUES ('b','B')")
    a = db.execute("SELECT id FROM topics WHERE slug='a'").fetchone()["id"]
    b = db.execute("SELECT id FROM topics WHERE slug='b'").fetchone()["id"]
    db.execute("INSERT INTO topic_prereqs (topic_id, prereq_topic_id) VALUES (?,?)", (b, a))
    n = db.execute("SELECT COUNT(*) AS c FROM topic_prereqs").fetchone()["c"]
    assert n == 1


def test_topic_prereqs_no_self_loop(db):
    db.execute("INSERT INTO topics (slug, name) VALUES ('a','A')")
    a = db.execute("SELECT id FROM topics WHERE slug='a'").fetchone()["id"]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO topic_prereqs (topic_id, prereq_topic_id) VALUES (?,?)", (a, a))


def test_weakness_profile_table(db):
    db.execute("INSERT INTO weakness_profile (pattern_tag, miss_count, total_count) VALUES ('dp-1d', 3, 8)")
    row = db.execute("SELECT * FROM weakness_profile WHERE pattern_tag='dp-1d'").fetchone()
    assert row["miss_count"] == 3 and row["total_count"] == 8


def test_sessions_has_outcome_ended_at_hints_used(db):
    cols = {r["name"] for r in db.execute("PRAGMA table_info(sessions)").fetchall()}
    assert "outcome" in cols
    assert "ended_at" in cols
    assert "hints_used_json" in cols


def test_sessions_outcome_check_constraint(db):
    db.execute("INSERT INTO questions (slug, title, statement, difficulty) VALUES ('x','X','...','easy')")
    qid = db.execute("SELECT id FROM questions WHERE slug='x'").fetchone()["id"]
    db.execute("INSERT INTO sessions (id, question_id, outcome) VALUES ('s1', ?, 'unaided')", (qid,))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO sessions (id, question_id, outcome) VALUES ('s2', ?, 'bogus')", (qid,))


def test_ensure_schema_idempotent_on_v0_5a_db(tmp_path):
    """Migration must not error on a v0.5a-shape DB (no outcome/ended_at on sessions)."""
    from whiteboard_mcp.db import connect, ensure_schema
    raw = sqlite3.connect(str(tmp_path / "coach.db"))
    raw.executescript("""
      CREATE TABLE questions (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL, statement TEXT NOT NULL, difficulty TEXT NOT NULL,
        leetcode_id INTEGER, topic_id INTEGER);
      CREATE TABLE sessions (id TEXT PRIMARY KEY, question_id INTEGER NOT NULL,
        started_at TIMESTAMP DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        current_step_id INTEGER);
      CREATE TABLE steps (id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER, ordinal INTEGER,
        description TEXT, pattern_tags TEXT, UNIQUE(question_id, ordinal));
      CREATE TABLE attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
        ordinal INTEGER, user_text TEXT, evaluator_json TEXT,
        ts TIMESTAMP DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), UNIQUE(session_id, ordinal));
      CREATE TABLE topics (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL);
      CREATE TABLE question_topics (question_id INTEGER, topic_id INTEGER, is_primary INTEGER, PRIMARY KEY(question_id, topic_id));
      CREATE TABLE hint_levels (id INTEGER PRIMARY KEY AUTOINCREMENT, step_id INTEGER, level INTEGER, text TEXT, UNIQUE(step_id, level));
    """)
    raw.commit(); raw.close()

    conn = connect(tmp_path / "coach.db")
    ensure_schema(conn)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    assert "outcome" in cols and "ended_at" in cols and "hints_used_json" in cols
    ensure_schema(conn)  # second call no-op
    conn.close()
