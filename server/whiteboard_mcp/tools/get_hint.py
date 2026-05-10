"""get_hint tool: returns the hint at the requested level for the user's
current step. Levels 1-3 escalate from gentle nudge to step-revealing.

Algo only - rejects SD sessions with not_supported_for_sd."""
from __future__ import annotations
import sqlite3

from whiteboard_mcp.errors import (
    invalid_level, no_current_step, not_found, not_supported_for_sd,
)


def get_hint(conn: sqlite3.Connection, session_id: str, level: int) -> dict:
    # Type-check before level validation: a wrong-tool error is more useful
    # than a wrong-argument error when the caller is on the wrong code path.
    session = conn.execute(
        "SELECT s.current_step_id, q.type "
        "FROM sessions s JOIN questions q ON q.id = s.question_id "
        "WHERE s.id = ?",
        (session_id,),
    ).fetchone()
    if not session:
        return not_found(entity="session", by="id", value=session_id)
    if session["type"] == "system_design":
        return not_supported_for_sd(tool="get_hint")

    if level not in (1, 2, 3):
        return invalid_level(got=level, valid=[1, 2, 3])

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
