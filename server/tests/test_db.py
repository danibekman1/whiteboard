import sqlite3

import pytest


def test_schema_creates_exact_v0_tables(db):
    # sqlite_sequence is auto-created for AUTOINCREMENT columns; filter it.
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert names == {"questions", "steps", "sessions", "attempts"}


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
