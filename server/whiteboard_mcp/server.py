"""FastMCP server entry point.

Streamable HTTP transport at /mcp. Ingests seed JSON at startup; tools
come online once the DB is ready.
"""
from __future__ import annotations
import contextlib
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
    with contextlib.closing(connect(DB_PATH)) as conn:
        ensure_schema(conn)
        n_q, n_s = ingest_seeds(conn, SEED_DIR)
        log.info("ingest complete: %d questions, %d steps", n_q, n_s)


def get_conn():
    """Per-call connection (sqlite3 connections are not thread-safe).

    Callers must wrap in `contextlib.closing(...)` so the connection is
    actually closed - sqlite3's own context manager only commits/rolls back.
    """
    return connect(DB_PATH)


@mcp.tool()
def get_next_question(slug: str | None = None) -> dict:
    """Pull a question and start a new coaching session.

    Optional slug picks a specific question (e.g. 'two-sum'). Omit for random.
    Returns {session_id, question: {slug, title, statement, difficulty}}.
    Canonical reasoning steps are NOT returned - they stay server-side so
    you cannot leak them to the candidate.

    Errors: {error: 'not_found', entity: 'question', ...} when slug is unknown
    or the question bank is empty.
    """
    with contextlib.closing(get_conn()) as conn:
        return _get_next_question(conn, slug=slug)


@mcp.tool()
def evaluate_attempt(session_id: str, user_text: str) -> dict:
    """Submit the candidate's latest message for evaluation.

    Runs the inner Opus evaluator against the question's canonical steps
    and the candidate's text. Returns:
      {step_ordinal: int, correct: bool, missing: list[str],
       suggested_move: 'nudge'|'advance'|'reanchor'|'wrap_up'}

    Errors:
      {error: 'not_found', entity: 'session', ...}    - unknown session_id
      {error: 'evaluator_parse_failed', raw: '...'}   - LLM produced no tool_use
      {error: 'evaluator_timeout'}                    - inner LLM exceeded timeout
      {error: 'internal_error', message: '...'}       - any other failure
    """
    with contextlib.closing(get_conn()) as conn:
        return _evaluate_attempt(conn, session_id=session_id, user_text=user_text)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    _bootstrap()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")


if __name__ == "__main__":
    main()
