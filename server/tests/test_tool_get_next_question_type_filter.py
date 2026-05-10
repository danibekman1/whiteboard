"""Type filter for get_next_question.

Default (no type, no slug) preserves existing behavior: algo random pick.
type='system_design' picks an SD question randomly. Slug overrides type:
slug='url-shortener' returns that specific question regardless of type
filter (or its absence)."""
from __future__ import annotations
from pathlib import Path

import pytest

from whiteboard_mcp.topic_seed_loader import ingest_topics
from whiteboard_mcp.tools.get_next_question import get_next_question
from bank.ingest import ingest_bank


SEED = Path(__file__).parent.parent / "bank" / "seed"
CURATED = SEED / "sd_curated"


def _bootstrap_mixed(db, tmp_path):
    """Ingest curated SDs + one algo so type filter has both populations."""
    import json
    ingest_topics(db, SEED / "topics.json")
    ingest_bank(db, CURATED)
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum-test.json").write_text(json.dumps({
        "slug": "two-sum-test", "title": "Two Sum Test",
        "statement": "Given an array of integers nums and a target...",
        "difficulty": "easy", "leetcode_id": 1, "topics": ["arrays-hashing"],
        "canonical_solution": {"language": "python",
            "code": "def two_sum(n,t): return [0,1]\n",
            "time": "O(n)", "space": "O(n)"},
        "test_cases": [{"input": [[2, 7], 9], "expected": [0, 1]}] * 3,
        "steps": [{"ordinal": i, "description": f"step {i} long enough",
                   "pattern_tags": ["t"],
                   "hints": [{"level": 1, "text": "h1"},
                             {"level": 2, "text": "h2"},
                             {"level": 3, "text": "h3"}]}
                  for i in range(1, 4)],
    }))
    ingest_bank(db, gen)


def test_default_picks_algo(db, tmp_path):
    """Pre-PR-4 contract preserved: no slug + no type -> algo."""
    _bootstrap_mixed(db, tmp_path)
    for _ in range(20):  # several iterations to guard against random luck
        result = get_next_question(db)
        assert "session_id" in result
        # Look up the type by slug.
        t = db.execute(
            "SELECT type FROM questions WHERE slug=?", (result["question"]["slug"],)
        ).fetchone()["type"]
        assert t == "algo"


def test_type_filter_picks_sd(db, tmp_path):
    _bootstrap_mixed(db, tmp_path)
    for _ in range(10):
        result = get_next_question(db, type="system_design")
        slug = result["question"]["slug"]
        assert slug in {"url-shortener", "parking-lot", "rate-limiter"}


def test_slug_overrides_type_filter(db, tmp_path):
    """If you ask for a specific slug, you get that slug regardless of type."""
    _bootstrap_mixed(db, tmp_path)
    result = get_next_question(db, slug="url-shortener", type="algo")
    assert result["question"]["slug"] == "url-shortener"


def test_type_filter_returns_not_found_when_no_questions_match(db):
    """SD bank empty -> type='system_design' returns not_found."""
    ingest_topics(db, SEED / "topics.json")
    # No SD questions ingested.
    result = get_next_question(db, type="system_design")
    assert result["error"] == "not_found"


def test_invalid_type_value_rejected(db, tmp_path):
    _bootstrap_mixed(db, tmp_path)
    result = get_next_question(db, type="not_a_real_type")
    # Pin the implementation contract rather than accept either error: a
    # future contract change to 'invalid_type' should be an explicit test
    # diff, not a silent swap.
    assert result == {
        "error": "not_found",
        "entity": "question",
        "by": "type",
        "value": "not_a_real_type",
    }
