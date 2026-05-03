"""Recommendation heuristic. Pure function over coach.db state.

No LLM call; deterministic; cheap to compute on every roadmap load.

Strategy in priority order:
  1. focus_topic given            -> easiest unsolved in that topic
  2. weakness drill                -> question with a weak pattern_tag (if user has any progress)
  3. topic step-up                 -> topic with all prereqs mastered, 0 solved
  4. difficulty step-up            -> in current focus topic, all easy cleared -> medium
  5. fresh start                   -> easiest in a no-prereq topic
  6. nothing left                  -> None
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass

DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}
MASTERY_THRESHOLD = 0.70
WEAKNESS_MIN_RATE = 0.40
WEAKNESS_MIN_TOTAL = 3


@dataclass
class Recommendation:
    question_slug: str
    topic_slug: str
    difficulty: str
    justification: str


def _topic_status(conn: sqlite3.Connection) -> dict[str, dict]:
    """Per-topic counts: total questions, solved (any non-skip), mastered (unaided/with_hints)."""
    rows = conn.execute(
        """
        SELECT t.slug AS topic, COUNT(DISTINCT q.id) AS total
        FROM topics t
        LEFT JOIN questions q ON q.topic_id = t.id
        GROUP BY t.slug
        """
    ).fetchall()
    status = {r["topic"]: {"total": r["total"], "solved": 0, "mastered": 0} for r in rows}

    latest = conn.execute(
        """
        SELECT q.id AS qid, t.slug AS topic, s.outcome
        FROM questions q
        JOIN topics t ON t.id = q.topic_id
        JOIN sessions s ON s.id = (
          SELECT id FROM sessions
          WHERE question_id = q.id AND outcome IS NOT NULL
          ORDER BY ended_at DESC LIMIT 1
        )
        """
    ).fetchall()
    for r in latest:
        topic = r["topic"]
        if topic not in status:
            continue
        if r["outcome"] != "skipped":
            status[topic]["solved"] += 1
        if r["outcome"] in ("unaided", "with_hints"):
            status[topic]["mastered"] += 1
    return status


def _is_mastered(s: dict) -> bool:
    if s["total"] == 0:
        return False
    return s["mastered"] / s["total"] >= MASTERY_THRESHOLD


def _topic_prereqs(conn: sqlite3.Connection) -> dict[str, list[str]]:
    rows = conn.execute(
        """
        SELECT t.slug AS topic, p.slug AS prereq
        FROM topic_prereqs e
        JOIN topics t ON t.id = e.topic_id
        JOIN topics p ON p.id = e.prereq_topic_id
        """
    ).fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["topic"], []).append(r["prereq"])
    return out


def _solved_question_ids(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute(
        """
        SELECT DISTINCT q.id FROM questions q
        JOIN sessions s ON s.question_id = q.id
        WHERE s.outcome IS NOT NULL AND s.outcome != 'skipped'
        """
    ).fetchall()
    return {r["id"] for r in rows}


def _easiest_unsolved_in_topic(
    conn: sqlite3.Connection,
    topic_slug: str,
    *,
    min_difficulty: str | None = None,
) -> dict | None:
    rows = conn.execute(
        """
        SELECT q.id, q.slug, q.difficulty, q.title
        FROM questions q
        JOIN topics t ON t.id = q.topic_id
        WHERE t.slug = ?
        ORDER BY CASE q.difficulty WHEN 'easy' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                 q.slug
        """,
        (topic_slug,),
    ).fetchall()
    solved = _solved_question_ids(conn)
    min_d = DIFFICULTY_ORDER.get(min_difficulty, -1) if min_difficulty else -1
    for r in rows:
        if r["id"] in solved:
            continue
        if DIFFICULTY_ORDER[r["difficulty"]] < min_d:
            continue
        return dict(r)
    return None


def _weak_patterns(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT pattern_tag FROM weakness_profile
        WHERE total_count >= ? AND (CAST(miss_count AS REAL) / total_count) >= ?
        ORDER BY (CAST(miss_count AS REAL) / total_count) DESC, total_count DESC
        """,
        (WEAKNESS_MIN_TOTAL, WEAKNESS_MIN_RATE),
    ).fetchall()
    return [r["pattern_tag"] for r in rows]


def _question_with_pattern(conn: sqlite3.Connection, pattern_tag: str) -> dict | None:
    """Find an unsolved question whose any step has this pattern_tag."""
    solved = _solved_question_ids(conn)
    rows = conn.execute(
        """
        SELECT DISTINCT q.id, q.slug, q.difficulty, q.title, t.slug AS topic
        FROM questions q
        JOIN topics t ON t.id = q.topic_id
        JOIN steps st ON st.question_id = q.id
        WHERE st.pattern_tags LIKE ?
        ORDER BY CASE q.difficulty WHEN 'easy' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                 q.slug
        """,
        (f'%"{pattern_tag}"%',),
    ).fetchall()
    for r in rows:
        if r["id"] not in solved:
            return dict(r)
    return None


def recommend_next(
    conn: sqlite3.Connection,
    *,
    focus_topic_slug: str | None = None,
) -> Recommendation | None:
    status = _topic_status(conn)
    prereqs = _topic_prereqs(conn)

    has_progress = any(s["solved"] > 0 for s in status.values())

    # 1. Focus topic
    if focus_topic_slug:
        focus_status = status.get(focus_topic_slug, {"total": 0, "solved": 0, "mastered": 0})
        q = _easiest_unsolved_in_topic(conn, focus_topic_slug)
        if q:
            # If user is starting fresh in this topic and any prereq was mastered,
            # frame the recommendation as "you nailed {prereq}".
            if focus_status["solved"] == 0:
                mastered_prereqs = [
                    p for p in prereqs.get(focus_topic_slug, [])
                    if _is_mastered(status.get(p, {"total": 0, "solved": 0, "mastered": 0}))
                ]
                if mastered_prereqs:
                    p = mastered_prereqs[0]
                    p_stat = status[p]
                    return Recommendation(
                        question_slug=q["slug"], topic_slug=focus_topic_slug,
                        difficulty=q["difficulty"],
                        justification=(
                            f"start {focus_topic_slug} - you nailed {p} "
                            f"({p_stat['mastered']}/{p_stat['total']})"
                        ),
                    )
            return Recommendation(
                question_slug=q["slug"], topic_slug=focus_topic_slug, difficulty=q["difficulty"],
                justification=f"continue {focus_topic_slug} - easiest unsolved here",
            )
        q = _easiest_unsolved_in_topic(conn, focus_topic_slug, min_difficulty="medium")
        if q:
            return Recommendation(
                question_slug=q["slug"], topic_slug=focus_topic_slug, difficulty=q["difficulty"],
                justification=f"you've cleared all easy in {focus_topic_slug} - try this medium",
            )
        # focus topic exhausted; fall through to general strategy

    # 2. Weakness drill (only if user has some progress)
    if has_progress:
        for tag in _weak_patterns(conn):
            q = _question_with_pattern(conn, tag)
            if q:
                rate = conn.execute(
                    "SELECT miss_count, total_count FROM weakness_profile WHERE pattern_tag = ?",
                    (tag,),
                ).fetchone()
                return Recommendation(
                    question_slug=q["slug"], topic_slug=q["topic"], difficulty=q["difficulty"],
                    justification=f"drill {tag} - {rate['miss_count']}/{rate['total_count']} miss rate",
                )

    # 3. Topic step-up - find topic where all prereqs mastered but topic untouched
    for topic, s in status.items():
        if s["total"] == 0 or s["solved"] > 0:
            continue
        topic_prereqs = prereqs.get(topic, [])
        if topic_prereqs and all(
            _is_mastered(status.get(p, {"total": 0, "solved": 0, "mastered": 0}))
            for p in topic_prereqs
        ):
            q = _easiest_unsolved_in_topic(conn, topic)
            if q:
                return Recommendation(
                    question_slug=q["slug"], topic_slug=topic, difficulty=q["difficulty"],
                    justification=(
                        f"ready to start {topic} - you cleared {len(topic_prereqs)} prereq(s)"
                    ),
                )

    # 4. Difficulty step-up - in-progress topic with all easies cleared, suggest a medium.
    # Sorted by slug for determinism. Skips topics already fully mastered (per spec, those
    # would have been satisfied by strategy 3 or be done).
    for topic in sorted(status.keys()):
        s = status[topic]
        if s["total"] == 0 or s["solved"] == 0 or _is_mastered(s):
            continue
        # Check if every easy question in this topic is solved.
        unsolved_easy = _easiest_unsolved_in_topic(conn, topic)
        if unsolved_easy and unsolved_easy["difficulty"] == "easy":
            continue  # there's still an easy left
        # All easies cleared; pick the easiest medium (or harder).
        q = _easiest_unsolved_in_topic(conn, topic, min_difficulty="medium")
        if q:
            return Recommendation(
                question_slug=q["slug"], topic_slug=topic, difficulty=q["difficulty"],
                justification=f"you've cleared all easy in {topic} - try this medium",
            )

    # 5. Fresh start (or fallback)
    for topic, s in status.items():
        if s["total"] == 0:
            continue
        if not prereqs.get(topic) and s["solved"] == 0:
            q = _easiest_unsolved_in_topic(conn, topic)
            if q:
                return Recommendation(
                    question_slug=q["slug"], topic_slug=topic, difficulty=q["difficulty"],
                    justification=f"begin here - {topic} has no prereqs",
                )

    # 6. Nothing left
    return None
