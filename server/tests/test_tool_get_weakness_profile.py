from whiteboard_mcp.tools.get_weakness_profile import get_weakness_profile


def test_returns_empty_when_no_data(db):
    out = get_weakness_profile(db)
    assert out == {"patterns": []}


def test_returns_sorted_by_miss_rate_then_total(db):
    db.execute(
        "INSERT INTO weakness_profile (pattern_tag, miss_count, total_count) VALUES ('low', 1, 10)"
    )
    db.execute(
        "INSERT INTO weakness_profile (pattern_tag, miss_count, total_count) VALUES ('high', 8, 10)"
    )
    db.execute(
        "INSERT INTO weakness_profile (pattern_tag, miss_count, total_count) VALUES ('mid', 5, 10)"
    )
    out = get_weakness_profile(db)
    tags = [p["pattern_tag"] for p in out["patterns"]]
    assert tags == ["high", "mid", "low"]
    assert out["patterns"][0]["miss_rate"] == 0.8


def test_skips_zero_total(db):
    db.execute(
        "INSERT INTO weakness_profile (pattern_tag, miss_count, total_count) VALUES ('untouched', 0, 0)"
    )
    out = get_weakness_profile(db)
    assert out["patterns"] == []
