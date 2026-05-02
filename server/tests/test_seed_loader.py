from pathlib import Path

from whiteboard_mcp.seed_loader import ingest_seeds, load_seed_dir

SEED_DIR = Path(__file__).parent.parent / "whiteboard_mcp" / "seed"


def test_load_seed_dir_finds_all_five():
    seeds = load_seed_dir(SEED_DIR)
    slugs = {s["slug"] for s in seeds}
    assert slugs == {
        "two-sum",
        "valid-parentheses",
        "reverse-linked-list",
        "binary-search",
        "climbing-stairs",
    }


def test_ingest_seeds_writes_questions_and_steps(db):
    n_questions, n_steps = ingest_seeds(db, SEED_DIR)
    assert n_questions == 5
    assert n_steps >= 25  # 6 + 6 + 5 + 6 + 6 = 29
    row = db.execute("SELECT * FROM questions WHERE slug='two-sum'").fetchone()
    assert row["title"] == "Two Sum"
    steps = db.execute(
        "SELECT * FROM steps WHERE question_id=? ORDER BY ordinal",
        (row["id"],),
    ).fetchall()
    assert steps[0]["ordinal"] == 1
    assert (
        "brute-force" in steps[0]["description"].lower()
        or "nested" in steps[0]["description"].lower()
    )


def test_ingest_seeds_is_idempotent(db):
    ingest_seeds(db, SEED_DIR)
    ingest_seeds(db, SEED_DIR)  # no errors, no dupes
    n = db.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
    assert n == 5
