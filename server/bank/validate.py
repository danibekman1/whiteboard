"""CLI: validate JSON files against schema (and correctness/complexity for algo).

Walks bank/generated/ (algo path: schema + correctness + complexity) and
bank/seed/sd_curated/ (SD path: schema-only round-trip). Dispatches per-file
on the JSON's `type` field (absent or 'algo' -> algo path; 'system_design'
-> SD path). Use --type to restrict to one track.

Usage:
    cd server && uv run python -m bank.validate
    cd server && uv run python -m bank.validate --type sd
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from bank import validator, sd_validator
from bank.validator import ValidationReport, summarize


def _peek_type(path: Path) -> str:
    """Return the JSON's `type` field, or 'algo' if absent or unparseable.
    Parse errors surface again in validate_one as a real failure."""
    try:
        return json.loads(path.read_text()).get("type", "algo")
    except (json.JSONDecodeError, OSError):
        return "algo"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=Path(__file__).parent / "generated")
    ap.add_argument("--csv", type=Path, default=Path(__file__).parent / "seed" / "optimal_complexity.csv")
    ap.add_argument("--type", choices=("algo", "sd", "all"), default="all",
                    help="restrict validation to one track (default: all)")
    args = ap.parse_args()

    files = sorted(args.dir.glob("*.json"))
    sd_curated = Path(__file__).parent / "seed" / "sd_curated"
    if sd_curated.exists():
        files += sorted(sd_curated.glob("*.json"))

    if args.type == "algo":
        files = [p for p in files if _peek_type(p) == "algo"]
    elif args.type == "sd":
        files = [p for p in files if _peek_type(p) == "system_design"]

    if not files:
        print(f"0 files matched type={args.type}")
        return 0

    reports: list[ValidationReport] = []
    for p in files:
        if _peek_type(p) == "system_design":
            res = sd_validator.validate_one(p)
            reports.append(ValidationReport(
                slug=p.stem,
                ok=res.ok,
                failures=[res.error] if res.error else [],
            ))
        else:
            reports.append(validator.validate_one(p, optimal_csv=args.csv))

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
