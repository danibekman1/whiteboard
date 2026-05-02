"""Upsert topics from bank/seed/topics.json into the topics table."""
from __future__ import annotations
import json
import sqlite3
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
