"""Pydantic round-trip tests for SD question JSON shape.

Mirrors tests/test_schemas.py for the algo path. Catches generation drift
before validation/ingest spends real time."""
from __future__ import annotations
import pytest
from pydantic import ValidationError

from bank.sd_schemas import SDQuestionJSON, PHASES_REQUIRED


def _valid_sd_question() -> dict:
    """Minimal valid SD question with all 5 phases, 3 checklist items each, 3 pushbacks."""
    phases = []
    for i, phase in enumerate(PHASES_REQUIRED, start=1):
        phases.append({
            "phase": phase,
            "ordinal": i,
            "checklist": [
                {"item": f"checklist item {j} for {phase} phase exists", "required": True}
                for j in range(3)
            ],
        })
    return {
        "slug": "url-shortener",
        "type": "system_design",
        "title": "URL Shortener",
        "statement": "Design a URL shortener service like bit.ly with high read traffic.",
        "difficulty": "medium",
        "scenario_tag": "high read traffic",
        "phases": phases,
        "pushbacks": [
            {"trigger_tag": "no_capacity_estimate",
             "trigger_desc": "Candidate proposes architecture before estimating QPS or storage",
             "response": "Wait - we don't know if this is 1k QPS or 1M QPS yet. Does it matter?"},
            {"trigger_tag": "single_db",
             "trigger_desc": "Candidate uses one DB for both reads and writes at scale",
             "response": "If reads outnumber writes 100:1, is one Postgres really enough?"},
            {"trigger_tag": "no_cache_discussion",
             "trigger_desc": "Candidate moves to deep dive without addressing read caching",
             "response": "We're at 1M reads/sec on a relational DB - what's protecting it?"},
        ],
    }


def test_valid_sd_question_round_trips():
    raw = _valid_sd_question()
    q = SDQuestionJSON.model_validate(raw)
    assert q.slug == "url-shortener"
    assert q.type == "system_design"
    assert len(q.phases) == 5
    assert tuple(p.phase for p in q.phases) == PHASES_REQUIRED
    assert len(q.pushbacks) == 3


def test_phases_must_be_exactly_five_in_order():
    raw = _valid_sd_question()
    raw["phases"] = raw["phases"][:4]  # only 4 phases
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_phases_must_be_in_canonical_order():
    raw = _valid_sd_question()
    raw["phases"][0], raw["phases"][1] = raw["phases"][1], raw["phases"][0]  # swap clarify and estimate
    with pytest.raises(ValidationError, match="phases must be exactly"):
        SDQuestionJSON.model_validate(raw)


def test_phase_ordinals_must_be_one_through_five():
    raw = _valid_sd_question()
    raw["phases"][2]["ordinal"] = 7
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_checklist_minimum_three_items_per_phase():
    raw = _valid_sd_question()
    raw["phases"][0]["checklist"] = raw["phases"][0]["checklist"][:2]  # only 2 items
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_checklist_maximum_eight_items_per_phase():
    raw = _valid_sd_question()
    raw["phases"][0]["checklist"] = [
        {"item": f"item {i} with enough length", "required": True} for i in range(9)
    ]
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_pushbacks_minimum_three():
    raw = _valid_sd_question()
    raw["pushbacks"] = raw["pushbacks"][:2]
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_pushback_trigger_tag_pattern():
    raw = _valid_sd_question()
    raw["pushbacks"][0]["trigger_tag"] = "Bad-Tag!"  # uppercase + symbols
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_type_must_be_system_design_literal():
    raw = _valid_sd_question()
    raw["type"] = "algo"
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_slug_pattern_rejects_uppercase():
    raw = _valid_sd_question()
    raw["slug"] = "URL-Shortener"
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)


def test_statement_minimum_length():
    raw = _valid_sd_question()
    raw["statement"] = "too short"
    with pytest.raises(ValidationError):
        SDQuestionJSON.model_validate(raw)
