"""CLI: generate (or refresh) bank/generated/<slug>.json for every Blind-75 seed entry.

Usage:
    cd server && uv run python -m bank.generate                # full run
    cd server && uv run python -m bank.generate --limit 5      # smoke run, 5 questions
    cd server && uv run python -m bank.generate --regenerate   # force rewrite

Cost: roughly N * 1.3 Opus calls (avg, with retries). 75 seeds ~= ~100 calls.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import anthropic

from bank.generator import (
    generate_with_retries,
    GenerationInput,
    GenerationFailed,
    NON_RETRYABLE_ERRORS,
)
from bank.validator import validate_one
from bank.schemas import QuestionJSON

ROOT = Path(__file__).parent
SEED_DIR = ROOT / "seed"
OUT_DIR = ROOT / "generated"


def _load_seeds() -> list[GenerationInput]:
    blind = json.loads((SEED_DIR / "blind75.json").read_text())
    optimal: dict[str, tuple[str, str]] = {}
    with (SEED_DIR / "optimal_complexity.csv").open() as fh:
        for row in csv.DictReader(fh):
            optimal[row["slug"]] = (row.get("time", "") or "", row.get("space", "") or "")
    seeds = []
    for entry in blind:
        t, s = optimal.get(entry["slug"], ("", ""))
        seeds.append(GenerationInput(
            slug=entry["slug"],
            title=entry["title"],
            difficulty=entry["difficulty"],
            topic=entry["topic"],
            leetcode_id=entry.get("leetcode_id"),
            optimal_time=t or None,
            optimal_space=s or None,
        ))
    return seeds


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def _existing_is_valid(out_path: Path) -> bool:
    if not out_path.exists():
        return False
    r = validate_one(out_path, optimal_csv=SEED_DIR / "optimal_complexity.csv")
    return r.ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--regenerate", action="store_true",
                    help="rewrite even if existing file validates")
    ap.add_argument("--only", type=str, default=None,
                    help="comma-separated list of slugs to run")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seeds = _load_seeds()
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        seeds = [s for s in seeds if s.slug in wanted]
    if args.limit:
        seeds = seeds[: args.limit]

    client = _client()
    failures: list[tuple[str, str]] = []
    skipped: list[str] = []
    succeeded: list[str] = []
    t0 = time.time()

    for i, seed in enumerate(seeds, start=1):
        out_path = OUT_DIR / f"{seed.slug}.json"
        if not args.regenerate and _existing_is_valid(out_path):
            skipped.append(seed.slug)
            print(f"[{i}/{len(seeds)}] skip {seed.slug} (already valid)")
            continue

        print(f"[{i}/{len(seeds)}] generating {seed.slug}...", flush=True)
        try:
            q: QuestionJSON = generate_with_retries(client=client, seed=seed)
        except GenerationFailed as e:
            print(f"  FAIL after {len(e.attempt_errors)} attempts")
            failures.append((seed.slug, e.attempt_errors[-1]))
            continue
        except NON_RETRYABLE_ERRORS as e:
            # Auth / billing / bad-request: every remaining seed will hit the
            # same wall, so fail the whole run with a clear message instead of
            # silently looping through 50 more seeds.
            print(f"\nABORT: non-retryable API error: {type(e).__name__}: {str(e)[:200]}")
            print("Fix the credential / billing issue and re-run; resumability "
                  "will skip already-valid files.")
            return 3

        out_path.write_text(json.dumps(q.model_dump(), indent=2))

        # Post-write validation: catches anything the schema lets through but
        # the validator's correctness/complexity checks would catch.
        r = validate_one(out_path, optimal_csv=SEED_DIR / "optimal_complexity.csv")
        if not r.ok:
            print(f"  POST-VALIDATION FAIL: {r.failures}")
            failures.append((seed.slug, "; ".join(r.failures)))
            continue
        succeeded.append(seed.slug)
        print(f"  OK")

    elapsed = time.time() - t0
    print(f"\n{len(succeeded)} new, {len(skipped)} skipped, {len(failures)} failed; {elapsed:.0f}s elapsed")
    if failures:
        print("\nFailed slugs:")
        for slug, err in failures:
            print(f"  {slug}: {err[:200]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
