"""Integration tests for bank.validate CLI - the type-dispatch routing.

Covers what test_sd_validator.py and test_bank_validator.py don't:
that bank.validate.main() correctly routes algo files to validator.validate_one
and SD files to sd_validator.validate_one based on the JSON's `type` field.

This is the load-bearing piece for PR 2's verification gate (boot smoke
expects 78 questions validated cleanly), so unit tests on the leaf
validators are not sufficient."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from unittest.mock import patch

from bank import validate as validate_cli
from bank.sd_schemas import SDQuestionJSON


def _valid_algo_json(slug: str) -> dict:
    fn_name = slug.replace("-", "_")
    return {
        "slug": slug,
        "title": "Algo",
        "statement": "An algorithmic problem statement that's long enough.",
        "difficulty": "easy",
        "leetcode_id": 1,
        "topics": ["arrays-hashing"],
        "canonical_solution": {
            "language": "python",
            "code": f"def {fn_name}(x):\n    return x\n",
            "time": "O(n)",
            "space": "O(1)",
        },
        "test_cases": [{"input": [i], "expected": i} for i in (1, 2, 3)],
        "steps": [{
            "ordinal": i,
            "description": f"step {i} long enough description",
            "pattern_tags": ["t"],
            "hints": [{"level": l, "text": f"h{l}"} for l in (1, 2, 3)],
        } for i in range(1, 4)],
    }


def _valid_sd_json(slug: str) -> dict:
    phases = []
    for i, phase in enumerate(
        ("clarify", "estimate", "high_level", "deep_dive", "tradeoffs"), start=1
    ):
        phases.append({
            "phase": phase,
            "ordinal": i,
            "checklist": [
                {"item": f"item {j} for {phase} phase has enough length", "required": True}
                for j in range(3)
            ],
        })
    return {
        "slug": slug,
        "type": "system_design",
        "title": "Test SD",
        "statement": "A long enough statement for the schema validator to accept.",
        "difficulty": "medium",
        "scenario_tag": "test scenario",
        "phases": phases,
        "pushbacks": [
            {"trigger_tag": f"tag_{i}",
             "trigger_desc": f"trigger description number {i} long enough",
             "response": f"adversarial response {i} long enough"}
            for i in range(3)
        ],
    }


def _run_cli(tmp_path: Path, monkeypatch, argv: list[str]) -> tuple[int, str]:
    """Invoke validate.main() with the given argv. Returns (exit_code, stdout).

    All tests pass --curated <empty-tmp-dir> to isolate from the real
    bank/seed/sd_curated/ contents."""
    empty_curated = tmp_path / "empty_curated"
    empty_curated.mkdir(exist_ok=True)
    full_argv = ["validate", "--curated", str(empty_curated)] + argv
    monkeypatch.setattr(sys, "argv", full_argv)
    captured = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: captured.append(" ".join(str(x) for x in a)))
    rc = validate_cli.main()
    return rc, "\n".join(captured)


def test_cli_routes_sd_files_to_sd_validator(tmp_path, monkeypatch):
    """SD JSON in --dir is validated through sd_validator (schema-only),
    not through the algo validator (which would crash on missing
    canonical_solution + test_cases)."""
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "url-shortener.json").write_text(json.dumps(_valid_sd_json("url-shortener")))

    rc, out = _run_cli(tmp_path, monkeypatch, ["--dir", str(gen), "--type", "sd"])
    assert rc == 0
    assert "1/1 valid" in out


def test_cli_routes_algo_files_to_algo_validator(tmp_path, monkeypatch):
    """Algo JSON in --dir is validated through validator.validate_one
    (schema + correctness + complexity), not sd_validator."""
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(_valid_algo_json("two-sum")))
    csv = tmp_path / "optimal.csv"
    csv.write_text("slug,time,space\n")  # empty CSV - no complexity targets

    rc, out = _run_cli(tmp_path, monkeypatch,
                       ["--dir", str(gen), "--csv", str(csv), "--type", "algo"])
    assert rc == 0
    assert "1/1 valid" in out


def test_cli_mixed_dir_routes_each_file_correctly(tmp_path, monkeypatch):
    """A directory containing both algo and SD JSON is routed per-file."""
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(_valid_algo_json("two-sum")))
    (gen / "url-shortener.json").write_text(json.dumps(_valid_sd_json("url-shortener")))
    csv = tmp_path / "optimal.csv"
    csv.write_text("slug,time,space\n")

    rc, out = _run_cli(tmp_path, monkeypatch,
                       ["--dir", str(gen), "--csv", str(csv), "--type", "all"])
    assert rc == 0
    assert "2/2 valid" in out


def test_cli_returns_2_when_no_files_anywhere(tmp_path, monkeypatch):
    """Empty --dir AND empty --curated -> exit 2 (CI signal: misconfigured bank)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    rc, _ = _run_cli(tmp_path, monkeypatch,
                     ["--dir", str(empty), "--type", "all"])
    assert rc == 2


def test_cli_returns_0_when_filter_narrows_to_zero(tmp_path, monkeypatch):
    """Files exist but the type filter excludes them all -> exit 0
    (benign 'nothing matched', not a misconfiguration)."""
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "two-sum.json").write_text(json.dumps(_valid_algo_json("two-sum")))
    csv = tmp_path / "optimal.csv"
    csv.write_text("slug,time,space\n")

    rc, out = _run_cli(tmp_path, monkeypatch,
                       ["--dir", str(gen), "--csv", str(csv), "--type", "sd"])
    assert rc == 0
    assert "0 files matched type=sd" in out


def test_cli_reports_failures_with_exit_1(tmp_path, monkeypatch):
    """A schema-failing SD JSON should produce exit 1 and a failure listing."""
    gen = tmp_path / "gen"
    gen.mkdir()
    bad = _valid_sd_json("broken")
    bad["phases"] = bad["phases"][:4]  # 4 phases - violates min_length=5
    (gen / "broken.json").write_text(json.dumps(bad))

    rc, out = _run_cli(tmp_path, monkeypatch, ["--dir", str(gen), "--type", "sd"])
    assert rc == 1
    assert "0/1 valid" in out
    assert "broken" in out
