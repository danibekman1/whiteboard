"""Load hand-authored question JSON files into coach.db."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path


def load_seed_dir(seed_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(seed_dir.glob("*.json"))]


def ingest_seeds(conn: sqlite3.Connection, seed_dir: Path) -> tuple[int, int]:
    """Idempotent insert: each seed is upserted by slug; steps are replaced wholesale."""
    seeds = load_seed_dir(seed_dir)
    n_questions = 0
    n_steps = 0
    for s in seeds:
        conn.execute(
            "INSERT INTO questions (slug, title, statement, difficulty) VALUES (?,?,?,?) "
            "ON CONFLICT(slug) DO UPDATE SET title=excluded.title, "
            "statement=excluded.statement, difficulty=excluded.difficulty",
            (s["slug"], s["title"], s["statement"], s["difficulty"]),
        )
        qid = conn.execute(
            "SELECT id FROM questions WHERE slug = ?", (s["slug"],)
        ).fetchone()["id"]
        conn.execute("DELETE FROM steps WHERE question_id = ?", (qid,))
        for step in s["steps"]:
            conn.execute(
                "INSERT INTO steps (question_id, ordinal, description, pattern_tags) "
                "VALUES (?,?,?,?)",
                (qid, step["ordinal"], step["description"], json.dumps(step["pattern_tags"])),
            )
            n_steps += 1
        n_questions += 1
    conn.commit()
    return n_questions, n_steps
