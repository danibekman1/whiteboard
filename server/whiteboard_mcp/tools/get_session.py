"""get_session tool: read-only metadata about an active session.

For algo sessions, returns the question (slug/title/statement/difficulty/type),
current step ordinal, attempts count, and outcome.

For SD sessions, additionally returns scenario_tag (null when unset), the
question's pushback library (so the outer coach has them in-context for
adversarial moves), and the current phase derived from the latest attempt's
evaluator JSON.

Canonical reasoning content (algo steps, SD checklist) is never returned -
the outer agent must not be able to leak it via this tool either."""
from __future__ import annotations
import json
import sqlite3

from whiteboard_mcp.errors import not_found

# Phase-to-ordinal map. Kept aligned with four sites that hard-code the
# phase set: sd_phases.ordinal CHECK constraint (1..5), the Phase Literal
# in sd_evaluator.py, the Phase Literal in bank/sd_schemas.py, and the
# client-side mirror PHASE_ORDINAL in web/components/Chat.tsx (used by the
# SSE consumer to update the phase tracker mid-session). If the phase set
# ever changes, all four sites need updating.
_PHASE_ORDINAL = {
    "clarify": 1, "estimate": 2, "high_level": 3,
    "deep_dive": 4, "tradeoffs": 5,
}


def _current_phase_from_attempts(conn: sqlite3.Connection, session_id: str) -> dict | None:
    """Read the latest attempt's evaluator_json and pull the phase. Returns
    {phase, ordinal} or None if no attempts yet / parse failure."""
    row = conn.execute(
        "SELECT evaluator_json FROM attempts WHERE session_id = ? "
        "ORDER BY ordinal DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    try:
        ev = json.loads(row["evaluator_json"])
    except (json.JSONDecodeError, TypeError):
        return None
    phase = ev.get("phase")
    if not phase:
        return None
    ordinal = _PHASE_ORDINAL.get(phase)
    if ordinal is None:
        return None
    return {"phase": phase, "ordinal": ordinal}


def _load_pushbacks(conn: sqlite3.Connection, question_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT trigger_tag, trigger_desc, response FROM sd_pushbacks "
        "WHERE question_id = ? ORDER BY id",
        (question_id,),
    ).fetchall()
    return [{"trigger_tag": r["trigger_tag"],
             "trigger_desc": r["trigger_desc"],
             "response": r["response"]} for r in rows]


def get_session(conn: sqlite3.Connection, session_id: str) -> dict:
    row = conn.execute("""
        SELECT s.id AS session_id, s.outcome, s.current_step_id,
               q.id AS question_id, q.slug, q.title, q.statement, q.difficulty,
               q.type, q.scenario_tag
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

    question: dict = {
        "slug": row["slug"],
        "title": row["title"],
        "statement": row["statement"],
        "difficulty": row["difficulty"],
        "type": row["type"],
    }

    payload: dict = {
        "session_id": row["session_id"],
        "question": question,
        "current_step_ordinal": current_step_ordinal,
        "current_phase": None,
        "attempts_count": attempts_count,
        "outcome": row["outcome"],
    }

    if row["type"] == "system_design":
        # Spec §3: scenario_tag is "SD only; null for algo". Always-present
        # for SD (value or null), omitted for algo - keeps the contract
        # explicit at the SD chat UI without leaking the field to algo.
        question["scenario_tag"] = row["scenario_tag"]
        payload["pushbacks"] = _load_pushbacks(conn, row["question_id"])
        payload["current_phase"] = _current_phase_from_attempts(conn, session_id)

    return payload
