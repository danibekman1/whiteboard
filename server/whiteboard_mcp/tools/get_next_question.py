"""get_next_question tool: pulls a question and starts a session.

Returns id + statement only. Canonical content (algo steps, SD checklist)
stays server-side so the outer agent cannot leak it to the candidate.

Filters:
  - slug: pick a specific question (overrides type filter)
  - type: 'algo' or 'system_design'. Optional. When omitted, business
    logic resolves to 'algo' so v0.6 callers (which never passed a type)
    keep their algo-only random pick. Pass 'system_design' explicitly to
    select an SD question.
"""
from __future__ import annotations
import random
import sqlite3
import uuid

from whiteboard_mcp.errors import not_found


VALID_TYPES = ("algo", "system_design")
# Business-logic fallback: when no type is passed, pre-PR-4 callers
# expected algo-only behavior (the bank had no SD rows yet). We resolve
# at the boundary rather than at the API surface so the contract stays
# explicit ("None means caller didn't ask").
_DEFAULT_TYPE = "algo"


def get_next_question(
    conn: sqlite3.Connection,
    slug: str | None = None,
    type: str | None = None,
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
        qtype = type if type is not None else _DEFAULT_TYPE
        if qtype not in VALID_TYPES:
            return not_found(entity="question", by="type", value=qtype)
        rows = conn.execute(
            "SELECT id, slug, title, statement, difficulty, type "
            "FROM questions WHERE type = ?",
            (qtype,),
        ).fetchall()
        if not rows:
            return not_found(entity="question", by="type", value=qtype)
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
