"""evaluate_attempt tool: runs the inner evaluator and persists the attempt."""
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
)
from whiteboard_mcp.evaluator import evaluate, get_anthropic_client

log = logging.getLogger(__name__)


def evaluate_attempt(
    conn: sqlite3.Connection,
    session_id: str,
    user_text: str,
) -> dict:
    session = conn.execute(
        "SELECT s.id, s.question_id, q.slug, q.statement "
        "FROM sessions s JOIN questions q ON q.id = s.question_id "
        "WHERE s.id = ?",
        (session_id,),
    ).fetchone()
    if not session:
        return not_found(entity="session", by="id", value=session_id)

    canonical = [
        {"ordinal": r["ordinal"], "description": r["description"]}
        for r in conn.execute(
            "SELECT ordinal, description FROM steps "
            "WHERE question_id = ? ORDER BY ordinal",
            (session["question_id"],),
        ).fetchall()
    ]

    try:
        result = evaluate(
            client=get_anthropic_client(),
            question_statement=session["statement"],
            canonical_steps=canonical,
            user_text=user_text,
        )
    except anthropic.APITimeoutError:
        log.warning("evaluator timed out for session=%s", session_id)
        return evaluator_timeout()
    except ValueError as e:
        log.warning("evaluator parse failed for session=%s: %s", session_id, e)
        return evaluator_parse_failed(raw=str(e))
    except Exception as e:
        # Log full traceback so the operator can diagnose; keep MCP response
        # opaque so we don't leak internals to the outer agent.
        log.exception("evaluator call failed for session=%s", session_id)
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
    step_row = conn.execute(
        "SELECT id FROM steps WHERE question_id = ? AND ordinal = ?",
        (session["question_id"], payload["step_ordinal"]),
    ).fetchone()
    if step_row:
        conn.execute(
            "UPDATE sessions SET current_step_id = ? WHERE id = ?",
            (step_row["id"], session_id),
        )
    else:
        log.warning(
            "evaluator returned out-of-range step_ordinal=%d for question_id=%d (session=%s); "
            "attempt persisted, current_step_id unchanged",
            payload["step_ordinal"], session["question_id"], session_id,
        )
    conn.commit()
    return payload
