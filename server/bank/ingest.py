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


def _ingest_one(conn: sqlite3.Connection, q: QuestionJSON, topics: dict[str, int]) -> None:
    primary_slug = q.topics[0]
    primary_id = topics.get(primary_slug)
    if primary_id is None:
        print(f"  warn: unknown topic {primary_slug!r} for {q.slug}", file=sys.stderr)

    conn.execute("""
        INSERT INTO questions (slug, title, statement, difficulty, leetcode_id, topic_id)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(slug) DO UPDATE SET
          title=excluded.title, statement=excluded.statement,
          difficulty=excluded.difficulty, leetcode_id=excluded.leetcode_id,
          topic_id=excluded.topic_id
    """, (q.slug, q.title, q.statement, q.difficulty, q.leetcode_id, primary_id))
    qid = conn.execute("SELECT id FROM questions WHERE slug=?", (q.slug,)).fetchone()["id"]

    # Replace steps + dependent hints + topic links.
    step_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM steps WHERE question_id=?", (qid,)).fetchall()]
    if step_ids:
        placeholders = ",".join("?" for _ in step_ids)
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
                print(f"  warn: unknown topic {t_slug!r} for {q.slug}", file=sys.stderr)
            continue
        conn.execute("""
            INSERT INTO question_topics (question_id, topic_id, is_primary)
            VALUES (?,?,?)
        """, (qid, t_id, 1 if i == 0 else 0))


def ingest_bank(conn: sqlite3.Connection, generated_dir: Path) -> int:
    topics = _topic_id_map(conn)
    files = sorted(generated_dir.glob("*.json"))
    n = 0
    for path in files:
        try:
            q = QuestionJSON.model_validate_json(path.read_text())
        except Exception as e:
            print(f"  skip {path.name}: schema invalid ({e})", file=sys.stderr)
            continue
        _ingest_one(conn, q, topics)
        n += 1
    conn.commit()
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
