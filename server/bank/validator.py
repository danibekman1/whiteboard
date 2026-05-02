"""Per-file validation: schema, complexity, correctness. Pure logic.
The CLI entry (validate.py) orchestrates over a directory."""
from __future__ import annotations
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from bank.schemas import QuestionJSON
from bank.complexity import equal as complexity_equal
from bank.correctness import check, FunctionNotFound, ExecutionTimeout


@dataclass
class ValidationReport:
    slug: str
    ok: bool
    failures: list[str] = field(default_factory=list)


def _load_optimal_csv(path: Path) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            slug = row["slug"].strip()
            t = (row.get("time") or "").strip()
            s = (row.get("space") or "").strip()
            if slug and (t or s):
                out[slug] = (t, s)
    return out


def validate_one(
    json_path: Path,
    *,
    optimal_csv: Path,
) -> ValidationReport:
    slug = json_path.stem
    failures: list[str] = []

    raw = json.loads(json_path.read_text())
    try:
        q = QuestionJSON.model_validate(raw)
    except ValidationError as e:
        return ValidationReport(slug=slug, ok=False, failures=[f"schema: {e}"])

    try:
        c = check(slug=q.slug, solution=q.canonical_solution, test_cases=q.test_cases)
        if not c.all_passed:
            failures.extend(f"correctness: {f}" for f in c.failures)
    except FunctionNotFound as e:
        failures.append(f"correctness: function not found ({e})")
    except ExecutionTimeout as e:
        failures.append(f"correctness: timeout ({e})")

    optimal = _load_optimal_csv(optimal_csv)
    if q.slug in optimal:
        opt_t, opt_s = optimal[q.slug]
        if opt_t and not complexity_equal(q.canonical_solution.time, opt_t):
            failures.append(f"complexity: time {q.canonical_solution.time!r} != optimal {opt_t!r}")
        if opt_s and not complexity_equal(q.canonical_solution.space, opt_s):
            failures.append(f"complexity: space {q.canonical_solution.space!r} != optimal {opt_s!r}")

    return ValidationReport(slug=slug, ok=not failures, failures=failures)


def summarize(reports: list[ValidationReport]) -> dict:
    passed = [r for r in reports if r.ok]
    failed = [r for r in reports if not r.ok]
    return {
        "total": len(reports),
        "passed": len(passed),
        "failed": len(failed),
        "failed_slugs": [r.slug for r in failed],
    }
