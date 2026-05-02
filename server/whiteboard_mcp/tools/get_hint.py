"""get_hint tool: returns the hint at the requested level for the user's
current step. Levels 1-3 escalate from gentle nudge to step-revealing."""
from __future__ import annotations
import sqlite3

from whiteboard_mcp.errors import not_found, invalid_level, no_current_step


def get_hint(conn: sqlite3.Connection, session_id: str, level: int) -> dict:
    if level not in (1, 2, 3):
        return invalid_level(got=level, valid=[1, 2, 3])

    session = conn.execute(
        "SELECT current_step_id FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        return not_found(entity="session", by="id", value=session_id)
    step_id = session["current_step_id"]
    if step_id is None:
        return no_current_step()

    step = conn.execute(
        "SELECT ordinal FROM steps WHERE id = ?", (step_id,)
    ).fetchone()
    hint = conn.execute(
        "SELECT text FROM hint_levels WHERE step_id = ? AND level = ?",
        (step_id, level),
    ).fetchone()
    if not hint:
        return not_found(entity="hint", by="step_id+level", value=(step_id, level))
    return {"level": level, "text": hint["text"], "step_ordinal": step["ordinal"]}
