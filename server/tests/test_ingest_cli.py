"""Integration tests for bank.ingest._cli - the boot-time overlay.

test_ingest_sd.py covers the in-process ingest_bank() function.
This file covers the _cli wrapper specifically: that it walks both
the --dir argument AND the on-disk bank/seed/sd_curated/ directory,
so curated SD content lands in coach.db at boot."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from bank import ingest as ingest_module


def _valid_sd_json(slug: str) -> dict:
    phases = []
    for i, phase in enumerate(
        ("clarify", "estimate", "high_level", "deep_dive", "tradeoffs"), start=1
    ):
        phases.append({
            "phase": phase,
            "ordinal": i,
            "checklist": [
                {"item": f"item {j} for {phase} phase has enough length", "required": True}
                for j in range(3)
            ],
        })
    return {
        "slug": slug,
        "type": "system_design",
        "title": "Test SD",
        "statement": "A long enough statement for the schema validator to accept.",
        "difficulty": "medium",
        "scenario_tag": "test scenario",
        "phases": phases,
        "pushbacks": [
            {"trigger_tag": f"tag_{i}",
             "trigger_desc": f"trigger description number {i} long enough",
             "response": f"adversarial response {i} long enough"}
            for i in range(3)
        ],
    }


def test_cli_walks_real_seed_sd_curated(tmp_path, monkeypatch, capsys):
    """The real bank/seed/sd_curated/ has 3 hand-curated files. Running _cli
    against an empty --dir should still ingest those 3 SD rows."""
    empty_gen = tmp_path / "empty_gen"
    empty_gen.mkdir()
    db_path = tmp_path / "coach.db"

    monkeypatch.setattr(sys, "argv", [
        "ingest", "--db", str(db_path), "--dir", str(empty_gen)
    ])
    rc = ingest_module._cli()
    assert rc == 0

    # The 3 curated SD questions should be in the DB now.
    from whiteboard_mcp.db import connect
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT slug, type FROM questions WHERE type='system_design' ORDER BY slug"
        ).fetchall()
        slugs = [r["slug"] for r in rows]
        assert slugs == ["parking-lot", "rate-limiter", "url-shortener"]

        out = capsys.readouterr().out
        assert "ingested 3 questions" in out
    finally:
        conn.close()


def test_cli_count_is_actual_db_total_not_call_sum(tmp_path, monkeypatch, capsys):
    """If we put one SD file in --dir AND the real seed/sd_curated has 3,
    ingest_bank is called twice. Ensure the printed count is the actual DB
    row count (4 distinct slugs) rather than a sum that could double-count
    on slug overlap."""
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "extra-sd.json").write_text(json.dumps(_valid_sd_json("extra-sd")))
    db_path = tmp_path / "coach.db"

    monkeypatch.setattr(sys, "argv", [
        "ingest", "--db", str(db_path), "--dir", str(gen)
    ])
    rc = ingest_module._cli()
    assert rc == 0

    out = capsys.readouterr().out
    # 1 from --dir + 3 from sd_curated = 4 distinct slugs
    assert "ingested 4 questions" in out


def test_cli_ingest_is_idempotent(tmp_path, monkeypatch, capsys):
    """Running _cli twice produces the same row count - no duplicates."""
    empty_gen = tmp_path / "empty_gen"
    empty_gen.mkdir()
    db_path = tmp_path / "coach.db"

    monkeypatch.setattr(sys, "argv", [
        "ingest", "--db", str(db_path), "--dir", str(empty_gen)
    ])
    ingest_module._cli()
    capsys.readouterr()  # discard first run output
    ingest_module._cli()
    out = capsys.readouterr().out
    assert "ingested 3 questions" in out
