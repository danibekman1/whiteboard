"""Lock-in test for hand-curated SD questions.

Asserts every file in bank/seed/sd_curated/ round-trips through SDQuestionJSON.
This catches manual edits that break the schema before they hit ingest."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from bank.sd_schemas import SDQuestionJSON

CURATED_DIR = Path(__file__).parent.parent / "bank" / "seed" / "sd_curated"
CURATED_FILES = sorted(CURATED_DIR.glob("*.json")) if CURATED_DIR.exists() else []


def test_curated_dir_has_at_least_three_files():
    """The v0.7 plan commits to 3 curated questions as generator few-shots.
    If this drops below 3, generator pass-rate is at risk - investigate before
    deleting."""
    assert len(CURATED_FILES) >= 3, (
        f"expected >=3 curated SD files in {CURATED_DIR}, got {len(CURATED_FILES)}"
    )


@pytest.mark.parametrize("path", CURATED_FILES, ids=[p.stem for p in CURATED_FILES])
def test_curated_file_round_trips(path: Path):
    raw = json.loads(path.read_text())
    SDQuestionJSON.model_validate(raw)


@pytest.mark.parametrize("path", CURATED_FILES, ids=[p.stem for p in CURATED_FILES])
def test_curated_filename_matches_slug(path: Path):
    raw = json.loads(path.read_text())
    assert raw["slug"] == path.stem, (
        f"slug {raw['slug']!r} does not match filename {path.stem!r}"
    )


def test_all_curated_slugs_appear_in_sd_classics():
    """sd_classics.json drives generation; curated slugs must be listed there
    (with type='system_design' equivalent metadata) so the generator skips them."""
    classics_path = CURATED_DIR.parent / "sd_classics.json"
    classics = json.loads(classics_path.read_text())
    classics_slugs = {row["slug"] for row in classics}
    for path in CURATED_FILES:
        slug = path.stem
        assert slug in classics_slugs, (
            f"curated slug {slug!r} missing from sd_classics.json"
        )
