"""Regression test: server.py:_bootstrap() must ingest both bank/generated/
and bank/seed/sd_curated/ on boot.

PR 2 wired this into the CLI (bank.ingest._cli) but missed the server
bootstrap. This test pins the contract so the next refactor doesn't drop
SD content again."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from whiteboard_mcp import server as srv


def _minimal_sd_json() -> dict:
    phases = []
    for i, phase in enumerate(
        ("clarify", "estimate", "high_level", "deep_dive", "tradeoffs"), start=1
    ):
        phases.append({
            "phase": phase,
            "ordinal": i,
            "checklist": [
                {"item": f"item {j} for {phase} long enough text", "required": True}
                for j in range(3)
            ],
        })
    return {
        "slug": "boot-smoke-sd",
        "type": "system_design",
        "title": "Boot Smoke SD",
        "statement": "Synthetic SD question for the bootstrap test, long enough to clear schema validation.",
        "difficulty": "easy",
        "scenario_tag": "synthetic",
        "phases": phases,
        "pushbacks": [
            {"trigger_tag": f"tag_{i}",
             "trigger_desc": f"description {i} long enough text",
             "response": f"response {i} long enough text"}
            for i in range(3)
        ],
    }


def test_bootstrap_ingests_seed_sd_curated(tmp_path: Path, monkeypatch):
    """Drop a synthetic SD JSON into a tmp seed/sd_curated dir, point the
    server's path constants at the tmp dir, run _bootstrap, assert the SD
    row landed in the DB."""
    db_path = tmp_path / "coach.db"
    bank_generated = tmp_path / "generated"
    bank_generated.mkdir()
    sd_curated = tmp_path / "sd_curated"
    sd_curated.mkdir()
    (sd_curated / "boot-smoke-sd.json").write_text(json.dumps(_minimal_sd_json()))

    # Re-point the module-level constants. Keep the topics seed pointing at
    # the real seed file so topic ingest doesn't fail.
    monkeypatch.setattr(srv, "DB_PATH", db_path)
    monkeypatch.setattr(srv, "BANK_DIR", bank_generated)
    # raising=True (the default) so a future rename of SD_CURATED_DIR breaks
    # this test rather than silently passing.
    monkeypatch.setattr(srv, "SD_CURATED_DIR", sd_curated)

    srv._bootstrap()

    from whiteboard_mcp.db import connect
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT type FROM questions WHERE slug='boot-smoke-sd'"
        ).fetchone()
    assert row is not None, "boot did not ingest seed/sd_curated/*.json"
    assert row["type"] == "system_design"
