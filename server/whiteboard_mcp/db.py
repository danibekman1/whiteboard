"""SQLite connection and v0 schema."""
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
"""


def connect(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()
