"""Ingest bank/generated/<slug>.json files into coach.db.

Dispatches per-file on the JSON's `type` field (absent or 'algo' -> algo
path; 'system_design' -> SD path). Both paths are idempotent: re-running
preserves the question's id so existing session FKs survive.

Algo path: replaces steps/hints/topics for each question. Side effect on
re-ingest: any in-flight session whose `current_step_id` points to a step
row about to be deleted gets its pointer set to NULL first (otherwise the
FK constraint blocks the delete). Callers of `get_hint` on those sessions
receive `no_current_step` until the candidate makes another attempt and
the evaluator reassigns `current_step_id`.

SD path: replaces sd_phases (CASCADE-deletes sd_checklist) and
sd_pushbacks. No session pointer to null - SD phase state lives in
`attempts.evaluator_json`, not on `sessions`."""
from __future__ import annotations
import json
import sqlite3
import sys
from pathlib import Path

from bank.schemas import QuestionJSON
from bank.sd_schemas import SDQuestionJSON


def _topic_id_map(conn: sqlite3.Connection) -> dict[str, int]:
    return {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM topics").fetchall()}


def _ingest_algo(
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
        INSERT INTO questions (slug, title, statement, difficulty, leetcode_id, topic_id, type)
        VALUES (?,?,?,?,?,?,'algo')
        ON CONFLICT(slug) DO UPDATE SET
          title=excluded.title, statement=excluded.statement,
          difficulty=excluded.difficulty, leetcode_id=excluded.leetcode_id,
          topic_id=excluded.topic_id, type='algo'
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


def _ingest_sd(conn: sqlite3.Connection, q: SDQuestionJSON) -> None:
    """Ingest one SD question. Idempotent on slug: replaces phases/checklist/
    pushbacks on re-ingest while preserving the questions.id (so existing
    session FKs survive)."""
    conn.execute("""
        INSERT INTO questions (slug, title, statement, difficulty, type, scenario_tag)
        VALUES (?,?,?,?,'system_design',?)
        ON CONFLICT(slug) DO UPDATE SET
          title=excluded.title, statement=excluded.statement,
          difficulty=excluded.difficulty, type='system_design',
          scenario_tag=excluded.scenario_tag
    """, (q.slug, q.title, q.statement, q.difficulty, q.scenario_tag))
    qid = conn.execute("SELECT id FROM questions WHERE slug=?", (q.slug,)).fetchone()["id"]

    # Replace phases (CASCADE deletes checklist via FK), then pushbacks.
    conn.execute("DELETE FROM sd_phases WHERE question_id=?", (qid,))
    conn.execute("DELETE FROM sd_pushbacks WHERE question_id=?", (qid,))

    for ph in q.phases:
        cur = conn.execute("""
            INSERT INTO sd_phases (question_id, phase, ordinal) VALUES (?,?,?)
        """, (qid, ph.phase, ph.ordinal))
        phase_id = cur.lastrowid
        for i, item in enumerate(ph.checklist, start=1):
            conn.execute("""
                INSERT INTO sd_checklist (phase_id, ordinal, item, required)
                VALUES (?,?,?,?)
            """, (phase_id, i, item.item, 1 if item.required else 0))

    for pb in q.pushbacks:
        conn.execute("""
            INSERT INTO sd_pushbacks (question_id, trigger_tag, trigger_desc, response)
            VALUES (?,?,?,?)
        """, (qid, pb.trigger_tag, pb.trigger_desc, pb.response))


def ingest_bank(conn: sqlite3.Connection, generated_dir: Path) -> int:
    topics = _topic_id_map(conn)
    files = sorted(generated_dir.glob("*.json"))
    unknown_secondary: set[str] = set()
    n = 0
    for path in files:
        # Per-file try: any failure (corrupt JSON, schema invalid, DB write
        # error) is logged and skipped so one bad file doesn't abort the run.
        try:
            raw = json.loads(path.read_text())
            # Dispatch on `type` field. Absent -> 'algo' (preserves v0.5a/v0.6
            # generated JSON which has no `type` field).
            qtype = raw.get("type", "algo")
            if qtype == "system_design":
                sd_q = SDQuestionJSON.model_validate(raw)
                _ingest_sd(conn, sd_q)
            else:
                algo_q = QuestionJSON.model_validate(raw)
                _ingest_algo(conn, algo_q, topics, unknown_secondary)
        except Exception as e:
            print(f"  skip {path.name}: {e}", file=sys.stderr)
            continue  # don't bump n on failure
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
        ingest_bank(conn, args.dir)
        # Also ingest curated SD questions (committed to git, not generated).
        # ingest_bank is idempotent on slug, so overlapping dirs are safe.
        sd_curated = Path(__file__).parent / "seed" / "sd_curated"
        if sd_curated.exists():
            ingest_bank(conn, sd_curated)
        # Print the actual row count, not the sum across calls (overlapping
        # slugs would double-count if we summed).
        total = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
        print(f"ingested {total} questions into {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
