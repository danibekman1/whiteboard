"""get_next_question tool: pulls a question and starts a session.

Returns id + statement only. Canonical steps stay server-side so the outer
agent cannot leak them to the candidate.
"""
from __future__ import annotations
import random
import sqlite3
import uuid

from whiteboard_mcp.errors import not_found


def get_next_question(
    conn: sqlite3.Connection,
    slug: str | None = None,
) -> dict:
    if slug:
        row = conn.execute(
            "SELECT id, slug, title, statement, difficulty FROM questions WHERE slug = ?",
            (slug,),
        ).fetchone()
        if not row:
            return not_found(entity="question", by="slug", value=slug)
    else:
        rows = conn.execute(
            "SELECT id, slug, title, statement, difficulty FROM questions"
        ).fetchall()
        if not rows:
            return not_found(entity="question", by="*", value="(empty bank)")
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
        },
    }
