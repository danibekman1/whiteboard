"""SQLite connection, schema, and column-add migrations."""
from __future__ import annotations
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS questions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  slug        TEXT NOT NULL UNIQUE,
  title       TEXT NOT NULL,
  statement   TEXT NOT NULL,
  difficulty  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS steps (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id   INTEGER NOT NULL REFERENCES questions(id),
  ordinal       INTEGER NOT NULL,
  description   TEXT NOT NULL,
  pattern_tags  TEXT NOT NULL,
  UNIQUE(question_id, ordinal)
);

CREATE TABLE IF NOT EXISTS sessions (
  id              TEXT PRIMARY KEY,
  question_id     INTEGER NOT NULL REFERENCES questions(id),
  started_at      TIMESTAMP DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  -- NULL until the first attempt is evaluated; updated by evaluate_attempt.
  current_step_id INTEGER REFERENCES steps(id)
);

CREATE TABLE IF NOT EXISTS attempts (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      TEXT NOT NULL REFERENCES sessions(id),
  ordinal         INTEGER NOT NULL,
  user_text       TEXT NOT NULL,
  evaluator_json  TEXT NOT NULL,
  ts              TIMESTAMP DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE(session_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id, ordinal);

-- v0.5a additions
CREATE TABLE IF NOT EXISTS topics (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  slug  TEXT NOT NULL UNIQUE,
  name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question_topics (
  question_id  INTEGER NOT NULL REFERENCES questions(id),
  topic_id     INTEGER NOT NULL REFERENCES topics(id),
  is_primary   INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (question_id, topic_id)
);

CREATE TABLE IF NOT EXISTS hint_levels (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  step_id  INTEGER NOT NULL REFERENCES steps(id),
  level    INTEGER NOT NULL CHECK (level BETWEEN 1 AND 3),
  text     TEXT NOT NULL,
  UNIQUE(step_id, level)
);
"""

# Columns added to existing tables in v0.5a. CREATE IF NOT EXISTS won't apply
# these to an already-created table, so we run ALTER TABLE explicitly when
# the column is missing. Idempotent: skips if column already present.
_QUESTIONS_NEW_COLUMNS = [
    ("leetcode_id", "INTEGER"),
    ("topic_id",    "INTEGER REFERENCES topics(id)"),
]


def connect(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    existing = _existing_columns(conn, "questions")
    for col, decl in _QUESTIONS_NEW_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE questions ADD COLUMN {col} {decl}")
    conn.commit()
