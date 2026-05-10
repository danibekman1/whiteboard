"""Schema-only validation for SD question JSON.

Mirrors bank/validator.py's report shape so the dispatcher in
bank/validate.py can format both paths uniformly. No correctness execution
(SD has no code to run), no complexity check (SD has no Big-O target)."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from bank.sd_schemas import SDQuestionJSON


@dataclass
class ValidationResult:
    path: Path
    ok: bool
    error: str | None = None


def validate_one(path: Path) -> ValidationResult:
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return ValidationResult(path=path, ok=False, error=f"json decode failed: {e}")

    try:
        SDQuestionJSON.model_validate(raw)
    except ValidationError as e:
        return ValidationResult(path=path, ok=False, error=str(e))

    return ValidationResult(path=path, ok=True)
