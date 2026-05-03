"""record_outcome tool: marks session done, updates weakness_profile.

For each pattern_tag attached to a step the user *attempted* in the session,
total_count is bumped by 1; miss_count is bumped by 1 only if at least one
attempt for that step was scored correct=False. Miss rate per tag is then
miss_count/total_count.

Idempotent: calling twice on the same session is a no-op for weakness counts
(checked via sessions.ended_at - if already set, we skip the bump)."""
from __future__ import annotations
import json
import sqlite3

from whiteboard_mcp.db import VALID_OUTCOMES
from whiteboard_mcp.errors import not_found, invalid_outcome


def _attempted_steps(conn: sqlite3.Connection, session_id: str) -> dict[int, dict]:
    """Return {step_ordinal -> {missed: bool, attempts: int}} from attempts table."""
    rows = conn.execute(
        "SELECT evaluator_json FROM attempts WHERE session_id = ? ORDER BY ordinal",
        (session_id,),
    ).fetchall()
    state: dict[int, dict] = {}
    for r in rows:
        ev = json.loads(r["evaluator_json"])
        ordinal = ev.get("step_ordinal")
        if ordinal is None:
            continue
        s = state.setdefault(ordinal, {"missed": False, "attempts": 0})
        s["attempts"] += 1
        if not ev.get("correct", False):
            s["missed"] = True
    return state


def record_outcome(
    conn: sqlite3.Connection,
    session_id: str,
    outcome: str,
    hints_used: list[dict],
) -> dict:
    if outcome not in VALID_OUTCOMES:
        return invalid_outcome(got=outcome, valid=list(VALID_OUTCOMES))
    session = conn.execute(
        "SELECT id, question_id, ended_at FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        return not_found(entity="session", by="id", value=session_id)

    already_ended = session["ended_at"] is not None

    conn.execute(
        "UPDATE sessions SET outcome = ?, "
        "ended_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
        "hints_used_json = ? WHERE id = ?",
        (outcome, json.dumps(hints_used), session_id),
    )

    weakness_updates: list[dict] = []
    if not already_ended:
        # Bump weakness_profile per pattern_tag of each *attempted* step.
        # A step counts as missed if any attempt for it had correct=False.
        attempted = _attempted_steps(conn, session_id)
        step_rows = conn.execute(
            "SELECT ordinal, pattern_tags FROM steps WHERE question_id = ?",
            (session["question_id"],),
        ).fetchall()
        ordinal_to_tags = {r["ordinal"]: json.loads(r["pattern_tags"]) for r in step_rows}

        per_tag: dict[str, dict] = {}
        for ord_, state in attempted.items():
            for tag in ordinal_to_tags.get(ord_, []):
                bucket = per_tag.setdefault(tag, {"miss": False, "total": 0})
                bucket["total"] += 1
                if state["missed"]:
                    bucket["miss"] = True

        for tag, agg in per_tag.items():
            conn.execute(
                """
                INSERT INTO weakness_profile (pattern_tag, miss_count, total_count, last_seen_session)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(pattern_tag) DO UPDATE SET
                  miss_count = miss_count + ?,
                  total_count = total_count + 1,
                  last_seen_session = excluded.last_seen_session
                """,
                (tag, 1 if agg["miss"] else 0, session_id, 1 if agg["miss"] else 0),
            )
            row = conn.execute(
                "SELECT miss_count, total_count FROM weakness_profile WHERE pattern_tag = ?",
                (tag,),
            ).fetchone()
            weakness_updates.append({
                "pattern_tag": tag,
                "miss_count": row["miss_count"],
                "total_count": row["total_count"],
            })

    conn.commit()
    return {"ok": True, "outcome": outcome, "weakness_updates": weakness_updates}
