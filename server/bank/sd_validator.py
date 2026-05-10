"""Schema-only validation for SD question JSON.

Returns the same ValidationReport shape as bank.validator.validate_one (algo
path), so the dispatcher in bank/validate.py needs no per-track adapter. No
correctness execution (SD has no code to run), no complexity check (SD has
no Big-O target)."""
from __future__ import annotations
import json
from pathlib import Path

from pydantic import ValidationError

from bank.sd_schemas import SDQuestionJSON
from bank.validator import ValidationReport


def validate_one(path: Path) -> ValidationReport:
    slug = path.stem
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return ValidationReport(slug=slug, ok=False, failures=[f"json decode failed: {e}"])

    try:
        SDQuestionJSON.model_validate(raw)
    except ValidationError as e:
        return ValidationReport(slug=slug, ok=False, failures=[f"schema: {e}"])

    return ValidationReport(slug=slug, ok=True, failures=[])
