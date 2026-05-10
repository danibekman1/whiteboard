"""Smoke tests for the SD eval harness.

Validates:
  - sd_cases.yaml parses and references real curated questions
  - run_sd_eval can be imported (catches typos before $$$ Opus call)
  - One case round-trips through the _check helper
  - Every case's pushback_triggered value (when asserted) matches a real
    trigger_tag in the curated bank file (catches case-vs-bank drift)
"""
from __future__ import annotations
import json
from pathlib import Path

import yaml

from whiteboard_mcp.sd_evaluator import SDEvaluatorOutput

ROOT = Path(__file__).parent.parent
CASES_PATH = ROOT / "eval" / "sd_cases.yaml"
CURATED = ROOT / "bank" / "seed" / "sd_curated"


def test_cases_yaml_parses_and_has_minimum_cases():
    cases = yaml.safe_load(CASES_PATH.read_text())
    assert isinstance(cases, list)
    # Designed for ~18 cases across 3 questions; floor at 15 so an
    # incidental case removal during iteration doesn't break this.
    assert len(cases) >= 15


def test_every_case_references_a_curated_slug():
    cases = yaml.safe_load(CASES_PATH.read_text())
    curated_slugs = {p.stem for p in CURATED.glob("*.json")}
    for c in cases:
        assert c["question_slug"] in curated_slugs, (
            f"case {c['name']} references unknown slug {c['question_slug']}"
        )


def test_every_case_has_required_keys():
    cases = yaml.safe_load(CASES_PATH.read_text())
    for c in cases:
        assert "name" in c
        assert "question_slug" in c
        assert "user_text" in c
        assert "expect" in c
        # At least one of phase/suggested_move/pushback_triggered must be asserted.
        assert any(
            k in c["expect"] for k in ("phase", "suggested_move", "pushback_triggered")
        ), f"case {c['name']} asserts nothing"


def test_every_pushback_trigger_tag_exists_in_its_bank_file():
    """Cases that assert pushback_triggered must reference a real trigger_tag
    in the corresponding sd_curated/<slug>.json. Catches case-vs-bank drift
    before the Opus call (saves an expensive failed run). Handles both
    scalar (single tag) and list (any-of) expectations; null in a list
    means "or no pushback at all" and is allowed without bank lookup."""
    cases = yaml.safe_load(CASES_PATH.read_text())
    banks: dict[str, set[str]] = {}
    for c in cases:
        if "pushback_triggered" not in c["expect"]:
            continue
        slug = c["question_slug"]
        if slug not in banks:
            data = json.loads((CURATED / f"{slug}.json").read_text())
            banks[slug] = {pb["trigger_tag"] for pb in data.get("pushbacks", [])}
        expected = c["expect"]["pushback_triggered"]
        candidates = expected if isinstance(expected, list) else [expected]
        for cand in candidates:
            if cand is None:
                continue  # null is "no pushback" - not a tag to validate
            assert cand in banks[slug], (
                f"case {c['name']} asserts pushback_triggered including "
                f"{cand!r} but {slug}.json defines tags "
                f"{sorted(banks[slug])!r}"
            )


def test_run_sd_eval_imports():
    """Catches import errors before someone pays for an Opus run."""
    from eval.run_sd_eval import main, _check, _load_question  # noqa: F401


def test_check_helper_phase_match():
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(phase="estimate", suggested_move="advance_phase")
    assert _check("t", {"phase": "estimate"}, actual) == []
    fails = _check("t", {"phase": "clarify"}, actual)
    assert len(fails) == 1
    assert "phase" in fails[0]


def test_check_helper_suggested_move_match():
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(phase="clarify", suggested_move="nudge")
    assert _check("t", {"suggested_move": "nudge"}, actual) == []
    fails = _check("t", {"suggested_move": "advance_phase"}, actual)
    assert len(fails) == 1


def test_check_helper_pushback_match():
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(
        phase="clarify",
        suggested_move="pushback",
        pushback_triggered="no_capacity_estimate",
    )
    assert _check("t", {"pushback_triggered": "no_capacity_estimate"}, actual) == []
    fails = _check("t", {"pushback_triggered": "different_tag"}, actual)
    assert len(fails) == 1
    assert "pushback_triggered" in fails[0]


def test_check_helper_pushback_mismatch_when_actual_is_none():
    """Case asserts a pushback fires; evaluator returned None. Should fail."""
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(
        phase="clarify", suggested_move="nudge", pushback_triggered=None
    )
    fails = _check("t", {"pushback_triggered": "naive_hashing"}, actual)
    assert len(fails) == 1


def test_check_helper_combines_multiple_fails():
    """Phase wrong AND suggested_move wrong should produce two messages."""
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(phase="clarify", suggested_move="nudge")
    fails = _check(
        "t",
        {"phase": "estimate", "suggested_move": "advance_phase"},
        actual,
    )
    assert len(fails) == 2


# --- List-valued expectations (any-of) -------------------------------------

def test_check_helper_accepts_list_phase_membership():
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(phase="clarify", suggested_move="nudge")
    # clarify is in the allowed set
    assert _check("t", {"phase": ["clarify", "estimate"]}, actual) == []


def test_check_helper_rejects_phase_outside_list():
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(phase="deep_dive", suggested_move="nudge")
    fails = _check("t", {"phase": ["clarify", "estimate"]}, actual)
    assert len(fails) == 1
    assert "deep_dive" in fails[0]


def test_check_helper_accepts_list_suggested_move_membership():
    from eval.run_sd_eval import _check
    actual = SDEvaluatorOutput(phase="clarify", suggested_move="press_on_missing")
    assert _check("t", {"suggested_move": ["nudge", "press_on_missing"]}, actual) == []


def test_check_helper_pushback_list_with_null_member():
    """A case that says 'either fire this pushback OR fire nothing' should
    accept both branches. Encoded as `[trigger_tag, null]`."""
    from eval.run_sd_eval import _check
    actual_null = SDEvaluatorOutput(
        phase="high_level", suggested_move="press_on_missing", pushback_triggered=None,
    )
    actual_fired = SDEvaluatorOutput(
        phase="high_level", suggested_move="pushback",
        pushback_triggered="no_failure_mode",
    )
    expected = {"pushback_triggered": ["no_failure_mode", None]}
    assert _check("t", expected, actual_null) == []
    assert _check("t", expected, actual_fired) == []
    # But a different tag still fails.
    actual_other = SDEvaluatorOutput(
        phase="high_level", suggested_move="pushback",
        pushback_triggered="fixed_window_only",
    )
    fails = _check("t", expected, actual_other)
    assert len(fails) == 1
