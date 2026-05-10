"""Tests for ingest dispatch on question.type.

Verifies:
  - SD JSON populates questions (type='system_design'), sd_phases,
    sd_checklist, sd_pushbacks
  - Algo JSON ingest still works (type='algo' set explicitly)
  - SD re-ingest is idempotent (replaces phases/checklist/pushbacks
    without leaving orphans)
  - JSON without `type` field defaults to algo (preserves v0.5a/v0.6
    behavior for already-generated bank/generated/*.json)
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from bank.ingest import ingest_bank
from whiteboard_mcp.topic_seed_loader import ingest_topics

SEED = Path(__file__).parent.parent / "bank" / "seed"


def _algo_json(slug: str = "two-sum") -> dict:
    return {
        "slug": slug,
        "title": "Two Sum",
        "statement": "Given an array of integers nums and a target...",
        "difficulty": "easy",
        "leetcode_id": 1,
        "topics": ["arrays-hashing"],
        "canonical_solution": {"language": "python",
                               "code": "def two_sum(n,t): return [0,1]\n",
                               "time": "O(n)", "space": "O(n)"},
        "test_cases": [{"input": [[2, 7], 9], "expected": [0, 1]} for _ in range(3)],
        "steps": [{"ordinal": i,
                   "description": f"step {i} long enough",
                   "pattern_tags": ["t"],
                   "hints": [{"level": 1, "text": "h1"},
                             {"level": 2, "text": "h2"},
                             {"level": 3, "text": "h3"}]}
                  for i in range(1, 4)],
    }


def _sd_json(slug: str = "url-shortener") -> dict:
    phases = []
    for i, phase in enumerate(
        ("clarify", "estimate", "high_level", "deep_dive", "tradeoffs"), start=1
    ):
        phases.append({
            "phase": phase,
            "ordinal": i,
            "checklist": [
                {"item": f"item {j} for {phase} phase exists", "required": True}
                for j in range(3)
            ],
        })
    return {
        "slug": slug,
        "type": "system_design",
        "title": "URL Shortener",
        "statement": "Design a URL shortener like bit.ly with high read traffic.",
        "difficulty": "medium",
        "scenario_tag": "high read traffic",
        "phases": phases,
        "pushbacks": [
            {"trigger_tag": "no_capacity_estimate",
             "trigger_desc": "Candidate proposes architecture before estimating QPS",
             "response": "Wait - we don't know if this is 1k QPS or 1M QPS yet."},
            {"trigger_tag": "single_db",
             "trigger_desc": "Candidate uses one DB for both reads and writes at scale",
             "response": "If reads outnumber writes 100:1, is one Postgres enough?"},
            {"trigger_tag": "no_cache",
             "trigger_desc": "Candidate skips read caching",
             "response": "1M reads/sec on a relational DB - what's protecting it?"},
        ],
    }


def test_sd_ingest_creates_phases_checklist_pushbacks(db, tmp_path):
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "url-shortener.json").write_text(json.dumps(_sd_json()))

    n = ingest_bank(db, gen)
    assert n == 1

    q = db.execute(
        "SELECT id, type FROM questions WHERE slug='url-shortener'"
    ).fetchone()
    assert q["type"] == "system_design"

    phases = db.execute(
        "SELECT phase, ordinal FROM sd_phases WHERE question_id=? "
        "ORDER BY ordinal", (q["id"],)
    ).fetchall()
    assert [p["phase"] for p in phases] == [
        "clarify", "estimate", "high_level", "deep_dive", "tradeoffs"
    ]

    cl = db.execute("""
        SELECT COUNT(*) AS c FROM sd_checklist
        WHERE phase_id IN (SELECT id FROM sd_phases WHERE question_id=?)
    """, (q["id"],)).fetchone()["c"]
    assert cl == 15  # 5 phases x 3 items

    # Verify per-phase distribution: 3 items each, none clumped on one phase.
    per_phase = db.execute("""
        SELECT p.phase, COUNT(c.id) AS n FROM sd_phases p
        LEFT JOIN sd_checklist c ON c.phase_id = p.id
        WHERE p.question_id=? GROUP BY p.id ORDER BY p.ordinal
    """, (q["id"],)).fetchall()
    assert all(r["n"] == 3 for r in per_phase)

    pb = db.execute(
        "SELECT COUNT(*) AS c FROM sd_pushbacks WHERE question_id=?", (q["id"],)
    ).fetchone()["c"]
    assert pb == 3


def test_algo_ingest_sets_type_algo_explicitly(db, tmp_path):
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(_algo_json()))

    ingest_bank(db, gen)
    row = db.execute("SELECT type FROM questions WHERE slug='two-sum'").fetchone()
    assert row["type"] == "algo"


def test_algo_json_without_type_field_defaults_to_algo(db, tmp_path):
    """v0.5a/v0.6 generated JSON has no `type` field; ingest treats absent
    as 'algo' to preserve existing bank/generated/ contents."""
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    raw = _algo_json()
    assert "type" not in raw  # confirm precondition
    (gen / "two-sum.json").write_text(json.dumps(raw))

    ingest_bank(db, gen)
    row = db.execute("SELECT type FROM questions WHERE slug='two-sum'").fetchone()
    assert row["type"] == "algo"


def test_sd_re_ingest_replaces_phases_no_orphans(db, tmp_path):
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "url-shortener.json").write_text(json.dumps(_sd_json()))

    ingest_bank(db, gen)
    qid = db.execute(
        "SELECT id FROM questions WHERE slug='url-shortener'"
    ).fetchone()["id"]
    first_phase_ids = {r["id"] for r in db.execute(
        "SELECT id FROM sd_phases WHERE question_id=?", (qid,)
    ).fetchall()}

    # Re-ingest with one fewer checklist item per phase.
    raw = _sd_json()
    for ph in raw["phases"]:
        ph["checklist"] = ph["checklist"][:3]  # still valid (>=3)
        ph["checklist"][0]["item"] = "modified item, still long enough"
    (gen / "url-shortener.json").write_text(json.dumps(raw))
    ingest_bank(db, gen)

    # Same question id (preserves session FKs).
    qid_after = db.execute(
        "SELECT id FROM questions WHERE slug='url-shortener'"
    ).fetchone()["id"]
    assert qid_after == qid

    # No orphaned phases or checklist rows.
    phases_now = db.execute(
        "SELECT COUNT(*) AS c FROM sd_phases WHERE question_id=?", (qid,)
    ).fetchone()["c"]
    assert phases_now == 5
    cl_now = db.execute("""
        SELECT COUNT(*) AS c FROM sd_checklist
        WHERE phase_id IN (SELECT id FROM sd_phases WHERE question_id=?)
    """, (qid,)).fetchone()["c"]
    assert cl_now == 15

    # Old phase rows are gone (CASCADE deleted on phase replacement).
    new_phase_ids = {r["id"] for r in db.execute(
        "SELECT id FROM sd_phases WHERE question_id=?", (qid,)
    ).fetchall()}
    assert new_phase_ids.isdisjoint(first_phase_ids)

    # Content fidelity: verify the modified item actually landed (not the
    # original "item 0..." string from the first ingest).
    modified = db.execute("""
        SELECT c.item FROM sd_checklist c
        JOIN sd_phases p ON c.phase_id = p.id
        WHERE p.question_id=? AND p.ordinal=1 AND c.ordinal=1
    """, (qid,)).fetchone()["item"]
    assert modified == "modified item, still long enough"


def test_sd_ingest_skips_malformed_json(db, tmp_path, capsys):
    """Mirror of the algo path's malformed-skip behavior: an SD JSON that
    fails Pydantic validation must be skipped with a stderr warning rather
    than aborting the whole ingest."""
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    bad = _sd_json()
    bad["phases"] = bad["phases"][:4]  # only 4 phases - fails min_length=5
    (gen / "bad.json").write_text(json.dumps(bad))

    n = ingest_bank(db, gen)
    assert n == 0
    assert "skip bad.json" in capsys.readouterr().err.lower()


def test_mixed_dir_ingests_both_types(db, tmp_path):
    ingest_topics(db, SEED / "topics.json")
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(_algo_json()))
    (gen / "url-shortener.json").write_text(json.dumps(_sd_json()))

    n = ingest_bank(db, gen)
    assert n == 2

    types = {r["slug"]: r["type"] for r in db.execute(
        "SELECT slug, type FROM questions"
    ).fetchall()}
    assert types == {"two-sum": "algo", "url-shortener": "system_design"}
