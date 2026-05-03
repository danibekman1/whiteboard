"""Ingest bank/generated/<slug>.json files into coach.db.

Idempotent: re-running replaces steps/hints/topics for each question, but
preserves the question's id (so existing sessions still resolve)."""
from __future__ import annotations
import json
import sqlite3
import sys
from pathlib import Path

from bank.schemas import QuestionJSON


def _topic_id_map(conn: sqlite3.Connection) -> dict[str, int]:
    return {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM topics").fetchall()}


def _ingest_one(
    conn: sqlite3.Connection,
    q: QuestionJSON,
    topics: dict[str, int],
    unknown_secondary: set[str],
) -> None:
    primary_slug = q.topics[0]
    primary_id = topics.get(primary_slug)
    if primary_id is None:
        # Loud: missing primary topic means the question has no primary
        # topic_id and won't be filterable by topic.
        print(f"  warn: unknown PRIMARY topic {primary_slug!r} for {q.slug}", file=sys.stderr)

    conn.execute("""
        INSERT INTO questions (slug, title, statement, difficulty, leetcode_id, topic_id)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(slug) DO UPDATE SET
          title=excluded.title, statement=excluded.statement,
          difficulty=excluded.difficulty, leetcode_id=excluded.leetcode_id,
          topic_id=excluded.topic_id
    """, (q.slug, q.title, q.statement, q.difficulty, q.leetcode_id, primary_id))
    qid = conn.execute("SELECT id FROM questions WHERE slug=?", (q.slug,)).fetchone()["id"]

    # Replace steps + dependent hints + topic links. Sessions may reference
    # the steps we're about to delete via current_step_id - NULL those out
    # first so the FK constraint doesn't block the DELETE.
    step_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM steps WHERE question_id=?", (qid,)).fetchall()]
    if step_ids:
        placeholders = ",".join("?" for _ in step_ids)
        conn.execute(
            f"UPDATE sessions SET current_step_id = NULL "
            f"WHERE current_step_id IN ({placeholders})",
            step_ids,
        )
        conn.execute(f"DELETE FROM hint_levels WHERE step_id IN ({placeholders})", step_ids)
        conn.execute("DELETE FROM steps WHERE question_id=?", (qid,))
    conn.execute("DELETE FROM question_topics WHERE question_id=?", (qid,))

    for step in q.steps:
        conn.execute("""
            INSERT INTO steps (question_id, ordinal, description, pattern_tags)
            VALUES (?,?,?,?)
        """, (qid, step.ordinal, step.description, json.dumps(step.pattern_tags)))
        sid = conn.execute(
            "SELECT id FROM steps WHERE question_id=? AND ordinal=?", (qid, step.ordinal)
        ).fetchone()["id"]
        for h in step.hints:
            conn.execute(
                "INSERT INTO hint_levels (step_id, level, text) VALUES (?,?,?)",
                (sid, h.level, h.text),
            )

    for i, t_slug in enumerate(q.topics):
        t_id = topics.get(t_slug)
        if t_id is None:
            if i > 0:
                # Quiet: secondary topics are best-effort. Collect for a
                # single end-of-run summary instead of one warning per slug.
                unknown_secondary.add(t_slug)
            continue
        conn.execute("""
            INSERT INTO question_topics (question_id, topic_id, is_primary)
            VALUES (?,?,?)
        """, (qid, t_id, 1 if i == 0 else 0))


def ingest_bank(conn: sqlite3.Connection, generated_dir: Path) -> int:
    topics = _topic_id_map(conn)
    files = sorted(generated_dir.glob("*.json"))
    unknown_secondary: set[str] = set()
    n = 0
    for path in files:
        try:
            q = QuestionJSON.model_validate_json(path.read_text())
        except Exception as e:
            print(f"  skip {path.name}: schema invalid ({e})", file=sys.stderr)
            continue
        _ingest_one(conn, q, topics, unknown_secondary)
        n += 1
    conn.commit()
    if unknown_secondary:
        print(
            f"  info: {len(unknown_secondary)} secondary topic slug(s) not in "
            f"taxonomy (linked questions kept their primary topic only): "
            f"{sorted(unknown_secondary)}",
            file=sys.stderr,
        )
    return n


def _cli() -> int:
    import argparse
    import contextlib
    from whiteboard_mcp.db import connect, ensure_schema
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=Path(__file__).parent.parent / "data" / "coach.db")
    ap.add_argument("--dir", type=Path, default=Path(__file__).parent / "generated")
    args = ap.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(connect(args.db)) as conn:
        ensure_schema(conn)
        n = ingest_bank(conn, args.dir)
        print(f"ingested {n} questions into {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
