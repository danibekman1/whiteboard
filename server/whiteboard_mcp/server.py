"""FastMCP server entry point.

Streamable HTTP transport at /mcp. Ingests seed JSON at startup; tools
come online once the DB is ready.
"""
from __future__ import annotations
import logging
from pathlib import Path

from fastmcp import FastMCP

from whiteboard_mcp.db import connect, ensure_schema
from whiteboard_mcp.seed_loader import ingest_seeds
from whiteboard_mcp.tools.evaluate_attempt import evaluate_attempt as _evaluate_attempt
from whiteboard_mcp.tools.get_next_question import get_next_question as _get_next_question

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "coach.db"
SEED_DIR = ROOT / "whiteboard_mcp" / "seed"

mcp = FastMCP("whiteboard-mcp")


def _bootstrap() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(DB_PATH)
    ensure_schema(conn)
    n_q, n_s = ingest_seeds(conn, SEED_DIR)
    log.info("ingest complete: %d questions, %d steps", n_q, n_s)
    conn.close()


def get_conn():
    """Per-call connection (sqlite3 connections are not thread-safe)."""
    return connect(DB_PATH)


@mcp.tool()
def get_next_question(slug: str | None = None) -> dict:
    """Pull a question and start a new coaching session.

    Optional slug picks a specific question (e.g. 'two-sum'). Omit for random.
    Returns {session_id, question: {slug, title, statement, difficulty}}.
    Canonical reasoning steps are NOT returned - they stay server-side so
    you cannot leak them to the candidate.
    """
    with get_conn() as conn:
        return _get_next_question(conn, slug=slug)


@mcp.tool()
def evaluate_attempt(session_id: str, user_text: str) -> dict:
    """Submit the candidate's latest message for evaluation.

    Runs the inner Opus evaluator against the question's canonical steps
    and the candidate's text. Returns:
      {step_id: int, correct: bool, missing: list[str],
       suggested_move: 'nudge'|'advance'|'reanchor'|'wrap_up'}

    On evaluator parse failure: {error: 'evaluator_parse_failed', raw: '...'}
    On unknown session_id: {error: 'not_found', ...}
    """
    with get_conn() as conn:
        return _evaluate_attempt(conn, session_id=session_id, user_text=user_text)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    _bootstrap()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")


if __name__ == "__main__":
    main()
