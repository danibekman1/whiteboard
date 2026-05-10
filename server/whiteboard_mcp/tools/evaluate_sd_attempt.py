"""evaluate_sd_attempt tool: runs the SD inner evaluator and persists the attempt.

Mirrors evaluate_attempt in shape; differs in the data it loads (phases +
checklist + pushbacks + session history rather than canonical linear steps)
and in the error variants it can return (adds wrong_question_type for the
algo-session case)."""
from __future__ import annotations
import json
import logging
import sqlite3

import anthropic

from whiteboard_mcp.errors import (
    evaluator_parse_failed,
    evaluator_timeout,
    internal_error,
    not_found,
    wrong_question_type,
)
from whiteboard_mcp.sd_evaluator import evaluate, get_anthropic_client

log = logging.getLogger(__name__)


def _load_phases(conn: sqlite3.Connection, question_id: int) -> list[dict]:
    """Phases ordered by ordinal; each carries its checklist (with id+required)."""
    phase_rows = conn.execute(
        "SELECT id, phase, ordinal FROM sd_phases WHERE question_id=? ORDER BY ordinal",
        (question_id,),
    ).fetchall()
    out = []
    for ph in phase_rows:
        items = conn.execute(
            "SELECT id, ordinal, item, required FROM sd_checklist "
            "WHERE phase_id=? ORDER BY ordinal",
            (ph["id"],),
        ).fetchall()
        out.append({
            "phase": ph["phase"],
            "ordinal": ph["ordinal"],
            "checklist": [
                {"id": it["id"], "item": it["item"], "required": bool(it["required"])}
                for it in items
            ],
        })
    return out


def _load_pushbacks(conn: sqlite3.Connection, question_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT trigger_tag, trigger_desc, response FROM sd_pushbacks WHERE question_id=?",
        (question_id,),
    ).fetchall()
    return [{"trigger_tag": r["trigger_tag"],
             "trigger_desc": r["trigger_desc"],
             "response": r["response"]} for r in rows]


def _load_history(conn: sqlite3.Connection, session_id: str) -> list[dict]:
    """Rebuild session_so_far from prior attempts. Each entry is the user_text
    plus the phase the evaluator resolved that turn to."""
    rows = conn.execute(
        "SELECT user_text, evaluator_json FROM attempts "
        "WHERE session_id=? ORDER BY ordinal",
        (session_id,),
    ).fetchall()
    out = []
    for r in rows:
        # If a prior attempt's evaluator_json is malformed, skip it - degrade
        # gracefully rather than failing the new turn.
        try:
            ev = json.loads(r["evaluator_json"])
            phase = ev.get("phase", "clarify")
        except json.JSONDecodeError:
            phase = "clarify"
        out.append({"phase": phase, "user_text": r["user_text"]})
    return out


def evaluate_sd_attempt(
    conn: sqlite3.Connection,
    session_id: str,
    user_text: str,
) -> dict:
    session = conn.execute(
        "SELECT s.id, s.question_id, q.slug, q.statement, q.type "
        "FROM sessions s JOIN questions q ON q.id = s.question_id "
        "WHERE s.id = ?",
        (session_id,),
    ).fetchone()
    if not session:
        return not_found(entity="session", by="id", value=session_id)
    if session["type"] != "system_design":
        return wrong_question_type(got=session["type"], expected="system_design")

    phases = _load_phases(conn, session["question_id"])
    pushbacks = _load_pushbacks(conn, session["question_id"])
    history = _load_history(conn, session_id)

    try:
        result = evaluate(
            client=get_anthropic_client(),
            question_statement=session["statement"],
            phases=phases,
            pushbacks=pushbacks,
            session_so_far=history,
            user_text=user_text,
        )
    except anthropic.APITimeoutError:
        log.warning("sd evaluator timed out for session=%s", session_id)
        return evaluator_timeout()
    except ValueError as e:
        log.warning("sd evaluator parse failed for session=%s: %s", session_id, e)
        return evaluator_parse_failed(raw=str(e))
    except Exception as e:
        log.exception("sd evaluator call failed for session=%s", session_id)
        return internal_error(message=f"evaluator call failed: {e!r}")

    payload = result.model_dump()
    next_ordinal = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) + 1 AS n FROM attempts WHERE session_id = ?",
        (session_id,),
    ).fetchone()["n"]
    conn.execute(
        "INSERT INTO attempts (session_id, ordinal, user_text, evaluator_json) "
        "VALUES (?,?,?,?)",
        (session_id, next_ordinal, user_text, json.dumps(payload)),
    )
    # Note: SD sessions do NOT update sessions.current_step_id (that field is
    # algo-only). Phase state is reconstructed from the latest attempt's
    # evaluator_json when needed (e.g. by get_session in PR 4).
    conn.commit()
    return payload
