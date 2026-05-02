from pathlib import Path
from bank.validator import validate_one, ValidationReport, summarize

FIXTURES = Path(__file__).parent / "fixtures" / "bank"
SEED_DIR = Path(__file__).parent.parent / "bank" / "seed"


def test_good_question_passes():
    r = validate_one(FIXTURES / "good_two_sum.json", optimal_csv=SEED_DIR / "optimal_complexity.csv")
    assert r.ok, r.failures


def test_wrong_complexity_caught():
    r = validate_one(FIXTURES / "bad_complexity.json", optimal_csv=SEED_DIR / "optimal_complexity.csv")
    assert not r.ok
    assert any("complexity" in f.lower() for f in r.failures)


def test_wrong_correctness_caught():
    r = validate_one(FIXTURES / "bad_correctness.json", optimal_csv=SEED_DIR / "optimal_complexity.csv")
    assert not r.ok
    assert any("case" in f.lower() for f in r.failures)


def test_summarize_groups_by_status():
    reports = [
        ValidationReport(slug="a", ok=True, failures=[]),
        ValidationReport(slug="b", ok=False, failures=["x"]),
        ValidationReport(slug="c", ok=True, failures=[]),
    ]
    s = summarize(reports)
    assert s["passed"] == 2 and s["failed"] == 1
    assert "b" in s["failed_slugs"]
