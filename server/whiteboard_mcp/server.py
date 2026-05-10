"""FastMCP server entry point.

Streamable HTTP transport at /mcp. At boot: ensures schema, ingests topic
seed, then ingests the bank (bank/generated/). The v0 hand-crafted seed
loader is retired; the bank pipeline is the source of truth.
"""
from __future__ import annotations
import contextlib
import logging
from pathlib import Path

from fastmcp import FastMCP

from whiteboard_mcp.db import connect, ensure_schema
from whiteboard_mcp.topic_seed_loader import ingest_topics, ingest_topic_prereqs
from bank.ingest import ingest_bank
from whiteboard_mcp.tools.evaluate_attempt import evaluate_attempt as _evaluate_attempt
from whiteboard_mcp.tools.evaluate_sd_attempt import evaluate_sd_attempt as _evaluate_sd_attempt
from whiteboard_mcp.tools.get_next_question import get_next_question as _get_next_question
from whiteboard_mcp.tools.get_hint import get_hint as _get_hint
from whiteboard_mcp.tools.record_outcome import record_outcome as _record_outcome
from whiteboard_mcp.tools.get_weakness_profile import get_weakness_profile as _get_weakness_profile
from whiteboard_mcp.tools.get_roadmap import get_roadmap as _get_roadmap
from whiteboard_mcp.tools.get_session import get_session as _get_session

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "coach.db"
TOPICS_SEED = ROOT / "bank" / "seed" / "topics.json"
PREREQS_SEED = ROOT / "bank" / "seed" / "topic_prereqs.json"
BANK_DIR = ROOT / "bank" / "generated"
SD_CURATED_DIR = ROOT / "bank" / "seed" / "sd_curated"

mcp = FastMCP("whiteboard-mcp")


def _bootstrap() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(connect(DB_PATH)) as conn:
        ensure_schema(conn)
        n_t = ingest_topics(conn, TOPICS_SEED)
        n_e = ingest_topic_prereqs(conn, PREREQS_SEED)
        n_q = ingest_bank(conn, BANK_DIR) if BANK_DIR.exists() else 0
        # Curated SD questions live in seed/ (committed to git, not generated).
        # Without this, FastMCP boot leaves coach.db with only algo questions.
        n_sd = ingest_bank(conn, SD_CURATED_DIR) if SD_CURATED_DIR.exists() else 0
        log.info(
            "boot: %d topics, %d prereqs, %d questions ingested (%d algo + %d sd)",
            n_t, n_e, n_q + n_sd, n_q, n_sd,
        )
        if n_q == 0:
            log.warning(
                "bank/generated/ is empty - run `python -m bank.generate` to populate"
            )


def get_conn():
    """Per-call connection (sqlite3 connections are not thread-safe).

    Callers must wrap in `contextlib.closing(...)` so the connection is
    actually closed - sqlite3's own context manager only commits/rolls back.
    """
    return connect(DB_PATH)


@mcp.tool()
def get_next_question(slug: str | None = None, type: str | None = None) -> dict:
    """Pull a question and start a new coaching session.

    Optional `slug` picks a specific question (e.g. 'two-sum', 'url-shortener').
    Optional `type` filters the random pick to 'algo' or 'system_design' when
    no slug is given. Slug always wins if both are passed.

    Always pass `type` explicitly when you have a preference. If omitted,
    the server falls back to 'algo' for back-compat with v0.6 callers; that
    fallback is business logic, not part of the contract, and may change.

    Returns {session_id, question: {slug, title, statement, difficulty, type}}.
    Canonical reasoning content (algo steps, SD checklist) is NOT returned -
    it stays server-side so you cannot leak it to the candidate.

    Errors: {error: 'not_found', entity: 'question', ...} when slug is unknown,
    or when no questions of the requested type exist.
    """
    with contextlib.closing(get_conn()) as conn:
        return _get_next_question(conn, slug=slug, type=type)


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


@mcp.tool()
def evaluate_sd_attempt(session_id: str, user_text: str) -> dict:
    """Submit the candidate's latest message for evaluation on an SD session.

    Runs the inner Opus evaluator against the question's phases, checklists,
    and pushbacks plus the candidate's text and prior session attempts.
    Returns:
      {phase, checklist_covered, checklist_missing_required,
       pushback_triggered, suggested_move}

    Use ONLY for system-design questions. For algo questions call
    evaluate_attempt instead - this tool returns
    {error: 'wrong_question_type', got, expected} if called on an algo
    session.

    Other errors:
      {error: 'not_found', entity: 'session', ...} - session_id unknown
      {error: 'evaluator_timeout'}                  - inner LLM exceeded 60s
      {error: 'evaluator_parse_failed', raw: ...}   - inner LLM returned malformed
      {error: 'internal_error', message: ...}       - unexpected failure
    """
    with contextlib.closing(get_conn()) as conn:
        return _evaluate_sd_attempt(conn, session_id=session_id, user_text=user_text)


@mcp.tool()
def get_hint(session_id: str, level: int) -> dict:
    """Reveal a hint for the candidate's current step.

    Levels:
      1 - gentle nudge ('what's the naive approach?')
      2 - directional ('two nested loops, what does that cost?')
      3 - step-revealing ('nested loop is O(n^2)')

    Use sparingly: prefer Socratic questions in your own response.
    Escalate the level only if the candidate explicitly asks for more help
    or has been visibly stuck for two turns. Returns
      {level, text, step_ordinal}
    or
      {error: 'no_current_step'}      # session hasn't been evaluated yet
      {error: 'invalid_level', ...}   # level not in {1,2,3}
      {error: 'not_found', ...}       # unknown session_id
    """
    with contextlib.closing(get_conn()) as conn:
        return _get_hint(conn, session_id=session_id, level=level)


@mcp.tool()
def record_outcome(session_id: str, outcome: str, hints_used: list[dict]) -> dict:
    """Mark a session complete and update the weakness profile.

    Call this when the candidate finishes a question (evaluator returned
    suggested_move='wrap_up') or quits partway ('partial').

    outcome:
      'unaided'         - completed without any hints
      'with_hints'      - completed but used at least one hint
      'partial'         - quit before finishing (still useful signal)
      'skipped'         - candidate said skip / can't make progress
      'revisit_flagged' - candidate or you flagged for re-attempt later

    hints_used: list of {'step_ordinal': int, 'level': int} entries the
    coach observed during this session. Pass [] if none.

    Returns {ok: true, outcome, weakness_updates: [{pattern_tag, miss_count,
    total_count}, ...]} or {error: ...}.
    """
    with contextlib.closing(get_conn()) as conn:
        return _record_outcome(
            conn, session_id=session_id, outcome=outcome, hints_used=hints_used,
        )


@mcp.tool()
def get_weakness_profile() -> dict:
    """Return per-pattern miss rates across all completed sessions.

    Returns {patterns: [{pattern_tag, miss_count, total_count, miss_rate}, ...]}
    sorted by miss_rate desc. Useful context for picking a drill question or
    framing your Socratic question (focus on the candidate's weakest pattern).
    """
    with contextlib.closing(get_conn()) as conn:
        return _get_weakness_profile(conn)


@mcp.tool()
def get_roadmap(focus_topic_slug: str | None = None) -> dict:
    """Return the topic DAG with per-topic progress, per-question status,
    a recommended-next pick, and the top weak patterns.

    Pass focus_topic_slug to bias the recommendation toward that topic.
    """
    with contextlib.closing(get_conn()) as conn:
        return _get_roadmap(conn, focus_topic_slug=focus_topic_slug)


@mcp.tool()
def get_session(session_id: str) -> dict:
    """Read metadata about an active session.

    Returns {session_id, question: {slug, title, statement, difficulty},
    current_step_ordinal, attempts_count, outcome}. Canonical reasoning
    steps are NOT returned - they stay server-side.

    Use when you need to remind yourself which question this session is on
    (e.g. after a navigation, or to ground a tool call). Cheap; safe to call
    at the start of any turn.
    """
    with contextlib.closing(get_conn()) as conn:
        return _get_session(conn, session_id=session_id)


@mcp.resource("roadmap://state")
def roadmap_state_resource() -> dict:
    """Roadmap state, exposed as a readable MCP resource. Same payload as
    get_roadmap() with no focus topic. Reading once at the start of a session
    lets the outer coach orient (which topics are unlocked, what's weak)."""
    with contextlib.closing(get_conn()) as conn:
        return _get_roadmap(conn, focus_topic_slug=None)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    _bootstrap()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")


if __name__ == "__main__":
    main()
