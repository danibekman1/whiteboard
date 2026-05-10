"""Tests for bank.sd_validator - schema-only validation of SD JSON files."""
from __future__ import annotations
import json
from pathlib import Path

from bank.sd_validator import validate_one


def _valid_sd_json() -> dict:
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
        "slug": "test-sd",
        "type": "system_design",
        "title": "Test",
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


def test_validate_one_accepts_valid_sd_json(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps(_valid_sd_json()))
    result = validate_one(p)
    assert result.ok is True
    assert result.failures == []
    assert result.slug == p.stem


def test_validate_one_rejects_missing_phase(tmp_path: Path):
    p = tmp_path / "x.json"
    raw = _valid_sd_json()
    raw["phases"] = raw["phases"][:4]
    p.write_text(json.dumps(raw))
    result = validate_one(p)
    assert result.ok is False
    assert any("phases" in f.lower() for f in result.failures)


def test_validate_one_rejects_too_few_pushbacks(tmp_path: Path):
    p = tmp_path / "x.json"
    raw = _valid_sd_json()
    raw["pushbacks"] = raw["pushbacks"][:2]
    p.write_text(json.dumps(raw))
    result = validate_one(p)
    assert result.ok is False


def test_validate_one_rejects_malformed_json(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{not valid json")
    result = validate_one(p)
    assert result.ok is False
    assert any("json" in f.lower() or "decode" in f.lower() for f in result.failures)


def test_validate_one_rejects_wrong_type_discriminator(tmp_path: Path):
    """sd_validator should reject JSON with type='algo' - the dispatcher in
    validate.py is responsible for routing, but if someone calls sd_validator
    directly on an algo file it should fail loudly, not silently."""
    p = tmp_path / "x.json"
    raw = _valid_sd_json()
    raw["type"] = "algo"
    p.write_text(json.dumps(raw))
    result = validate_one(p)
    assert result.ok is False


def test_validate_one_rejects_too_few_checklist_items(tmp_path: Path):
    p = tmp_path / "x.json"
    raw = _valid_sd_json()
    raw["phases"][0]["checklist"] = raw["phases"][0]["checklist"][:2]
    p.write_text(json.dumps(raw))
    result = validate_one(p)
    assert result.ok is False


def test_validate_one_rejects_bad_pushback_trigger_tag(tmp_path: Path):
    p = tmp_path / "x.json"
    raw = _valid_sd_json()
    raw["pushbacks"][0]["trigger_tag"] = "Has-Uppercase-And-Hyphens"
    p.write_text(json.dumps(raw))
    result = validate_one(p)
    assert result.ok is False
