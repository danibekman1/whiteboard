"""CLI: validate every JSON in bank/generated/ against schema, correctness, complexity.

Usage:
    cd server && uv run python -m bank.validate
    cd server && uv run python -m bank.validate --dir bank/generated --csv bank/seed/optimal_complexity.csv
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from bank.validator import validate_one, summarize


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=Path(__file__).parent / "generated")
    ap.add_argument("--csv", type=Path, default=Path(__file__).parent / "seed" / "optimal_complexity.csv")
    args = ap.parse_args()

    json_files = sorted(args.dir.glob("*.json"))
    if not json_files:
        print(f"no JSON files under {args.dir}", file=sys.stderr)
        return 2

    reports = [validate_one(p, optimal_csv=args.csv) for p in json_files]
    s = summarize(reports)
    print(f"\n{s['passed']}/{s['total']} valid; failures: {len(s['failed_slugs'])}")
    if s["failed_slugs"]:
        print("\nFailed:")
        for r in reports:
            if not r.ok:
                print(f"  {r.slug}:")
                for f in r.failures:
                    print(f"    - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
