"""Upsert topics from bank/seed/topics.json into the topics table."""
from __future__ import annotations
import json
import sqlite3
import sys
from pathlib import Path


def ingest_topics(conn: sqlite3.Connection, topics_json: Path) -> int:
    data = json.loads(topics_json.read_text())
    n = 0
    for entry in data:
        conn.execute(
            "INSERT INTO topics (slug, name) VALUES (?, ?) "
            "ON CONFLICT(slug) DO UPDATE SET name=excluded.name",
            (entry["slug"], entry["name"]),
        )
        n += 1
    conn.commit()
    return n


def ingest_topic_prereqs(conn: sqlite3.Connection, prereqs_json: Path) -> int:
    data = json.loads(prereqs_json.read_text())
    topic_ids = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM topics").fetchall()}
    n = 0
    for edge in data:
        t_id = topic_ids.get(edge["topic"])
        p_id = topic_ids.get(edge["prereq"])
        if t_id is None or p_id is None:
            missing = [
                f"topic '{edge['topic']}'" if t_id is None else None,
                f"prereq '{edge['prereq']}'" if p_id is None else None,
            ]
            joined = " and ".join(m for m in missing if m)
            print(f"  warn: unknown topic in edge {edge} ({joined})", file=sys.stderr)
            continue
        conn.execute(
            "INSERT INTO topic_prereqs (topic_id, prereq_topic_id) VALUES (?, ?) "
            "ON CONFLICT (topic_id, prereq_topic_id) DO NOTHING",
            (t_id, p_id),
        )
        n += 1
    _assert_acyclic(conn)
    conn.commit()
    return n


def _assert_acyclic(conn: sqlite3.Connection) -> None:
    """Topo-sort the prereq DAG; raise ValueError if it has a cycle.

    Self-loops are blocked by the schema CHECK constraint, but cycles of
    length ≥2 (e.g. a -> b -> a) would slip past the DB and break the
    recommendation heuristic, which assumes a DAG. Catch them at boot.
    """
    edges = conn.execute(
        "SELECT topic_id, prereq_topic_id FROM topic_prereqs"
    ).fetchall()
    if not edges:
        return
    # Adjacency list: prereq -> [dependents]. We DFS from each node and
    # detect a back-edge into the in-progress stack.
    adj: dict[int, list[int]] = {}
    nodes: set[int] = set()
    for r in edges:
        adj.setdefault(r["prereq_topic_id"], []).append(r["topic_id"])
        nodes.add(r["topic_id"]); nodes.add(r["prereq_topic_id"])
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}

    def visit(n: int, stack: list[int]) -> None:
        color[n] = GRAY
        stack.append(n)
        for m in adj.get(n, []):
            if color[m] == GRAY:
                cycle = stack[stack.index(m):] + [m]
                raise ValueError(f"cycle detected in topic_prereqs: {cycle}")
            if color[m] == WHITE:
                visit(m, stack)
        stack.pop()
        color[n] = BLACK

    for n in nodes:
        if color[n] == WHITE:
            visit(n, [])
