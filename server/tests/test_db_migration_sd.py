"""Migration tests for v0.7 SD schema delta.

Verifies that ensure_schema() on a v0.6 coach.db (no `type` column, no SD
tables) idempotently:
  - adds the `type` column with DEFAULT 'algo' (backfilling the 75 algo rows)
  - creates sd_phases, sd_checklist, sd_pushbacks tables
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

import pytest

from whiteboard_mcp.db import connect, ensure_schema


def _v06_questions_table(conn: sqlite3.Connection) -> None:
    """Recreate the v0.6 questions table shape (no `type` column)."""
    conn.executescript("""
        CREATE TABLE questions (
          id          INTEGER PRIMARY KEY AUTOINCREMENT,
          slug        TEXT NOT NULL UNIQUE,
          title       TEXT NOT NULL,
          statement   TEXT NOT NULL,
          difficulty  TEXT NOT NULL,
          leetcode_id INTEGER,
          topic_id    INTEGER
        );
        INSERT INTO questions (slug, title, statement, difficulty)
        VALUES
          ('two-sum', 'Two Sum', 'Given an array...', 'easy'),
          ('valid-anagram', 'Valid Anagram', 'Given two strings...', 'easy');
    """)
    conn.commit()


def test_type_column_added_with_default_algo(tmp_path: Path):
    db = tmp_path / "v06.db"
    with connect(db) as conn:
        _v06_questions_table(conn)
        # Verify pre-state: no `type` column, 2 rows.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
        assert "type" not in cols
        assert conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"] == 2

        # Run migration.
        ensure_schema(conn)

        # `type` column exists.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
        assert "type" in cols
        # Existing rows backfilled to 'algo'.
        rows = conn.execute("SELECT slug, type FROM questions ORDER BY slug").fetchall()
        assert all(r["type"] == "algo" for r in rows)


def test_sd_tables_created(tmp_path: Path):
    db = tmp_path / "fresh.db"
    with connect(db) as conn:
        ensure_schema(conn)
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "sd_phases" in tables
        assert "sd_checklist" in tables
        assert "sd_pushbacks" in tables


def test_sd_phases_check_constraints(tmp_path: Path):
    db = tmp_path / "fresh.db"
    with connect(db) as conn:
        ensure_schema(conn)
        conn.execute("INSERT INTO questions (slug, title, statement, difficulty, type) "
                     "VALUES ('q1', 't', 's', 'easy', 'system_design')")
        qid = conn.execute("SELECT id FROM questions WHERE slug='q1'").fetchone()["id"]
        # Bad phase name rejected.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO sd_phases (question_id, phase, ordinal) "
                         "VALUES (?, 'not_a_phase', 1)", (qid,))
        # Bad ordinal rejected.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO sd_phases (question_id, phase, ordinal) "
                         "VALUES (?, 'clarify', 7)", (qid,))


def test_questions_type_check_constraint(tmp_path: Path):
    db = tmp_path / "fresh.db"
    with connect(db) as conn:
        ensure_schema(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO questions (slug, title, statement, difficulty, type) "
                         "VALUES ('q1', 't', 's', 'easy', 'totally_invalid')")


def test_migration_is_idempotent(tmp_path: Path):
    db = tmp_path / "fresh.db"
    with connect(db) as conn:
        ensure_schema(conn)
        ensure_schema(conn)  # second run should not raise
        ensure_schema(conn)  # third run for good measure
        # Schema is stable.
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert {"questions", "sd_phases", "sd_checklist", "sd_pushbacks"} <= tables
