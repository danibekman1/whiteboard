"""SQLite connection, schema, and column-add migrations."""
from __future__ import annotations
import sqlite3
from pathlib import Path

# Single source of truth for the session outcome enum. Used both in the
# sessions.outcome CHECK constraint below and in record_outcome's input
# validation. If you add an outcome, update only this tuple.
VALID_OUTCOMES = ("unaided", "with_hints", "partial", "skipped", "revisit_flagged")
_OUTCOME_CHECK = ",".join(f"'{v}'" for v in VALID_OUTCOMES)

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

-- v0.6 additions
CREATE TABLE IF NOT EXISTS topic_prereqs (
  topic_id         INTEGER NOT NULL REFERENCES topics(id),
  prereq_topic_id  INTEGER NOT NULL REFERENCES topics(id),
  PRIMARY KEY (topic_id, prereq_topic_id),
  CHECK (topic_id != prereq_topic_id)
);

CREATE TABLE IF NOT EXISTS weakness_profile (
  pattern_tag        TEXT PRIMARY KEY,
  miss_count         INTEGER NOT NULL DEFAULT 0,
  total_count        INTEGER NOT NULL DEFAULT 0,
  -- nullable to allow read-tool unit tests to insert rows without a session;
  -- production writes (record_outcome) always populate it. FK guards against
  -- orphaned session ids ageing into the table.
  last_seen_session  TEXT REFERENCES sessions(id)
);
"""

# Columns added to existing tables across versions. CREATE IF NOT EXISTS won't
# apply these to an already-created table, so we run ALTER TABLE explicitly when
# the column is missing. Idempotent: skips if column already present.
_QUESTIONS_NEW_COLUMNS = [  # v0.5a
    ("leetcode_id", "INTEGER"),
    ("topic_id",    "INTEGER REFERENCES topics(id)"),
]

_SESSIONS_NEW_COLUMNS = [  # v0.6
    ("outcome",         f"TEXT CHECK (outcome IS NULL OR outcome IN ({_OUTCOME_CHECK}))"),
    ("ended_at",        "TIMESTAMP"),
    ("hints_used_json", "TEXT"),
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
    for table, new_cols in [("questions", _QUESTIONS_NEW_COLUMNS),
                            ("sessions", _SESSIONS_NEW_COLUMNS)]:
        existing = _existing_columns(conn, table)
        for col, decl in new_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    conn.commit()
