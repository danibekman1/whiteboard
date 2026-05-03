"""get_weakness_profile tool: returns pattern-tag miss rates."""
from __future__ import annotations
import sqlite3


def get_weakness_profile(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT pattern_tag, miss_count, total_count
        FROM weakness_profile
        WHERE total_count > 0
        """
    ).fetchall()
    patterns = [
        {
            "pattern_tag": r["pattern_tag"],
            "miss_count": r["miss_count"],
            "total_count": r["total_count"],
            "miss_rate": r["miss_count"] / r["total_count"] if r["total_count"] else 0.0,
        }
        for r in rows
    ]
    patterns.sort(key=lambda p: (-p["miss_rate"], -p["total_count"], p["pattern_tag"]))
    return {"patterns": patterns}
