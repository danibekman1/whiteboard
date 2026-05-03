"""get_session tool: read-only metadata about an active session.

Returns the question (slug/title/statement/difficulty), the candidate's
current step ordinal, count of attempts, and outcome (null until session
ends). Canonical steps are never returned - the outer agent must not be
able to leak them via this tool either."""
from __future__ import annotations
import sqlite3

from whiteboard_mcp.errors import not_found


def get_session(conn: sqlite3.Connection, session_id: str) -> dict:
    row = conn.execute("""
        SELECT s.id AS session_id, s.outcome, s.current_step_id,
               q.slug, q.title, q.statement, q.difficulty
        FROM sessions s
        JOIN questions q ON q.id = s.question_id
        WHERE s.id = ?
    """, (session_id,)).fetchone()
    if not row:
        return not_found(entity="session", by="id", value=session_id)

    current_step_ordinal = None
    if row["current_step_id"] is not None:
        step = conn.execute(
            "SELECT ordinal FROM steps WHERE id = ?", (row["current_step_id"],)
        ).fetchone()
        if step:
            current_step_ordinal = step["ordinal"]

    attempts_count = conn.execute(
        "SELECT COUNT(*) AS c FROM attempts WHERE session_id = ?", (session_id,)
    ).fetchone()["c"]

    return {
        "session_id": row["session_id"],
        "question": {
            "slug": row["slug"],
            "title": row["title"],
            "statement": row["statement"],
            "difficulty": row["difficulty"],
        },
        "current_step_ordinal": current_step_ordinal,
        "attempts_count": attempts_count,
        "outcome": row["outcome"],
    }
