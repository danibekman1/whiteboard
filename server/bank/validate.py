"""CLI: validate JSON files against schema (and correctness/complexity for algo).

Walks bank/generated/ (algo path: schema + correctness + complexity) and
bank/seed/sd_curated/ (SD path: schema-only round-trip). Dispatches per-file
on the JSON's `type` field (absent or 'algo' -> algo path; 'system_design'
-> SD path). Use --type to restrict to one track.

Exit codes: 0 = clean (or filter narrowed to 0 files), 1 = validation
failures, 2 = nothing to validate at all (both source dirs empty).

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
from bank.validator import summarize


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
    ap.add_argument("--curated", type=Path,
                    default=Path(__file__).parent / "seed" / "sd_curated",
                    help="directory of hand-curated SD JSON (also walked unconditionally)")
    ap.add_argument("--type", choices=("algo", "sd", "all"), default="all",
                    help="restrict validation to one track (default: all)")
    args = ap.parse_args()

    all_files = sorted(args.dir.glob("*.json"))
    if args.curated.exists():
        all_files += sorted(args.curated.glob("*.json"))

    # Preserve the v0.5a contract: empty source dirs is a hard error (exit 2)
    # so CI catches a missing/misconfigured bank. A type filter narrowing
    # N>0 files to 0 is a benign "nothing to do here" (exit 0).
    if not all_files:
        print(f"no JSON files under {args.dir} or {args.curated}", file=sys.stderr)
        return 2

    if args.type == "algo":
        files = [p for p in all_files if _peek_type(p) == "algo"]
    elif args.type == "sd":
        files = [p for p in all_files if _peek_type(p) == "system_design"]
    else:
        files = all_files

    if not files:
        print(f"0 files matched type={args.type}")
        return 0

    reports = []
    for p in files:
        if _peek_type(p) == "system_design":
            reports.append(sd_validator.validate_one(p))
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
