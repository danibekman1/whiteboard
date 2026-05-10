"""get_roadmap tool: full DAG state + per-topic progress + recommended next."""
from __future__ import annotations
import sqlite3

from whiteboard_mcp.recommend import (
    recommend_next, _topic_status, _topic_prereqs, _is_mastered,
)
from whiteboard_mcp.tools.get_weakness_profile import get_weakness_profile

_DIFF_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def _topic_status_string(status: dict, prereqs: list[str], status_map: dict) -> str:
    if _is_mastered(status):
        return "mastered"
    if status["solved"] > 0:
        return "in_progress"
    # No progress yet.
    if not prereqs or all(
        _is_mastered(status_map.get(p, {"total": 0, "solved": 0, "mastered": 0}))
        for p in prereqs
    ):
        return "unlocked"
    return "locked"


def _question_status(latest_outcome: str | None, topic_status: str) -> str:
    if latest_outcome is None:
        return "locked" if topic_status == "locked" else "unsolved"
    return latest_outcome


def get_roadmap(
    conn: sqlite3.Connection,
    focus_topic_slug: str | None = None,
) -> dict:
    status_map = _topic_status(conn)
    prereqs = _topic_prereqs(conn)

    topics_out = []
    for slug, s in status_map.items():
        ts = _topic_status_string(s, prereqs.get(slug, []), status_map)
        name_row = conn.execute("SELECT name FROM topics WHERE slug = ?", (slug,)).fetchone()
        topics_out.append({
            "slug": slug,
            "name": name_row["name"] if name_row else slug,
            "status": ts,
            "total": s["total"],
            "solved": s["solved"],
            "mastered": s["mastered"],
            "prereqs": prereqs.get(slug, []),
        })
    topics_out.sort(key=lambda t: t["slug"])
    topic_status_lookup = {t["slug"]: t["status"] for t in topics_out}

    edges = [
        {"from": prereq, "to": topic}
        for topic, prereq_list in prereqs.items()
        for prereq in prereq_list
    ]
    edges.sort(key=lambda e: (e["from"], e["to"]))

    rows = conn.execute(
        """
        SELECT q.slug, q.title, q.difficulty, t.slug AS topic_slug,
          (SELECT outcome FROM sessions
             WHERE question_id = q.id AND outcome IS NOT NULL
             ORDER BY ended_at DESC LIMIT 1) AS latest_outcome
        FROM questions q
        LEFT JOIN topics t ON t.id = q.topic_id
        WHERE q.type = 'algo'
        ORDER BY q.slug
        """
    ).fetchall()
    questions_out = []
    for r in rows:
        topic_st = topic_status_lookup.get(r["topic_slug"], "unlocked")
        st = _question_status(r["latest_outcome"], topic_st)
        questions_out.append({
            "slug": r["slug"],
            "title": r["title"],
            "difficulty": r["difficulty"],
            "topic_slug": r["topic_slug"],
            "status": st,
            "starred": st == "revisit_flagged",
        })

    # SD questions live in the same `questions` table but are surfaced in a
    # separate array - the algo `questions[]` above is filtered to type='algo'
    # so SD slugs don't accidentally appear in the algo grid.
    sd_rows = conn.execute(
        """
        SELECT q.slug, q.title, q.difficulty, q.scenario_tag,
          (SELECT outcome FROM sessions
             WHERE question_id = q.id AND outcome IS NOT NULL
             ORDER BY ended_at DESC LIMIT 1) AS latest_outcome
        FROM questions q
        WHERE q.type = 'system_design'
        """
    ).fetchall()
    sd_questions = [
        {"slug": r["slug"], "title": r["title"], "difficulty": r["difficulty"],
         "scenario_tag": r["scenario_tag"], "latest_outcome": r["latest_outcome"]}
        for r in sd_rows
    ]
    sd_questions.sort(key=lambda q: (_DIFF_ORDER.get(q["difficulty"], 99), q["slug"]))

    rec = recommend_next(conn, focus_topic_slug=focus_topic_slug)
    recommendation = (
        {
            "question_slug": rec.question_slug,
            "topic_slug": rec.topic_slug,
            "difficulty": rec.difficulty,
            "justification": rec.justification,
        }
        if rec is not None else None
    )

    weakness = get_weakness_profile(conn)["patterns"][:5]

    return {
        "topics": topics_out,
        "edges": edges,
        "questions": questions_out,
        "sd_questions": sd_questions,
        "recommendation": recommendation,
        "weakness": weakness,
    }
