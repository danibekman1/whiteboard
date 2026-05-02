"""Sandboxed correctness checker.

Spawns a subprocess to run the candidate solution against test cases. NOT a
strict security sandbox - assumes generated code is from our own Opus and run
on our own machine. Timeouts protect against infinite loops; subprocess
isolation protects against accidental import-time side effects. That's the
trust boundary for v0.5a. Tighten when we ship hosted."""
from __future__ import annotations
import json
import subprocess
import sys
import textwrap
from dataclasses import dataclass

from bank.schemas import CanonicalSolution, TestCase


class FunctionNotFound(Exception):
    ...


class ExecutionTimeout(Exception):
    ...


@dataclass
class CheckResult:
    all_passed: bool
    failures: list[str]


def _func_name_from_slug(slug: str) -> str:
    return slug.replace("-", "_")


_RUNNER_TEMPLATE = r"""
import json, sys
{code}
fn = globals().get({fn_name!r})
if fn is None:
    print(json.dumps({{"error": "function_not_found", "expected": {fn_name!r}}}))
    sys.exit(2)
results = []
cases = {cases_json}
for i, c in enumerate(cases):
    try:
        actual = fn(*c["input"])
        ok = actual == c["expected"]
        results.append({{"i": i, "ok": ok, "actual": actual, "expected": c["expected"]}})
    except Exception as e:
        results.append({{"i": i, "ok": False, "exception": repr(e), "expected": c["expected"]}})
print(json.dumps(results))
"""


def check(
    *,
    slug: str,
    solution: CanonicalSolution,
    test_cases: list[TestCase],
    timeout_s: float = 10.0,
) -> CheckResult:
    fn = _func_name_from_slug(slug)
    cases_json = json.dumps([{"input": c.input, "expected": c.expected} for c in test_cases])
    runner = _RUNNER_TEMPLATE.format(
        code=textwrap.dedent(solution.code),
        fn_name=fn,
        cases_json=cases_json,
    )
    try:
        cp = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        raise ExecutionTimeout(f"{slug} exceeded {timeout_s}s") from e

    if cp.returncode == 2:
        raise FunctionNotFound(f"{fn!r} not defined in {slug} solution")
    if cp.returncode != 0:
        return CheckResult(all_passed=False, failures=[f"runner exit={cp.returncode}: {cp.stderr.strip()}"])

    results = json.loads(cp.stdout.strip().splitlines()[-1])
    failures = [
        f"case {r['i']}: actual={r.get('actual')!r}, expected={r['expected']!r}"
        + (f" (exception: {r['exception']})" if "exception" in r else "")
        for r in results if not r["ok"]
    ]
    return CheckResult(all_passed=not failures, failures=failures)
