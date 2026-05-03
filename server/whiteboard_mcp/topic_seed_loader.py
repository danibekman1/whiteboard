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
            print(f"  warn: unknown topic in edge {edge}", file=sys.stderr)
            continue
        conn.execute(
            "INSERT INTO topic_prereqs (topic_id, prereq_topic_id) VALUES (?, ?) "
            "ON CONFLICT (topic_id, prereq_topic_id) DO NOTHING",
            (t_id, p_id),
        )
        n += 1
    conn.commit()
    return n
