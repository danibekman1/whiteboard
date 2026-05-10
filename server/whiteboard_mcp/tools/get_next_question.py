"""get_next_question tool: pulls a question and starts a session.

Returns id + statement only. Canonical content (algo steps, SD checklist)
stays server-side so the outer agent cannot leak it to the candidate.

Filters:
  - slug: pick a specific question (overrides type filter)
  - type: 'algo' (default), 'system_design'. Random pick within the filter.
"""
from __future__ import annotations
import random
import sqlite3
import uuid

from whiteboard_mcp.errors import not_found


VALID_TYPES = ("algo", "system_design")


def get_next_question(
    conn: sqlite3.Connection,
    slug: str | None = None,
    type: str = "algo",
) -> dict:
    if slug:
        row = conn.execute(
            "SELECT id, slug, title, statement, difficulty, type "
            "FROM questions WHERE slug = ?",
            (slug,),
        ).fetchone()
        if not row:
            return not_found(entity="question", by="slug", value=slug)
    else:
        if type not in VALID_TYPES:
            return not_found(entity="question", by="type", value=type)
        rows = conn.execute(
            "SELECT id, slug, title, statement, difficulty, type "
            "FROM questions WHERE type = ?",
            (type,),
        ).fetchall()
        if not rows:
            return not_found(entity="question", by="type", value=type)
        row = random.choice(rows)

    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, question_id) VALUES (?, ?)",
        (session_id, row["id"]),
    )
    conn.commit()
    return {
        "session_id": session_id,
        "question": {
            "slug": row["slug"],
            "title": row["title"],
            "statement": row["statement"],
            "difficulty": row["difficulty"],
            "type": row["type"],
        },
    }
