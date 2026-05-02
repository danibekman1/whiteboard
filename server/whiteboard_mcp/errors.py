"""Structured tool error builders. See design §8."""
from __future__ import annotations
from typing import Any


def not_found(entity: str, by: str, value: Any) -> dict:
    return {"error": "not_found", "entity": entity, "by": by, "value": value}


def evaluator_parse_failed(raw: str) -> dict:
    return {"error": "evaluator_parse_failed", "raw": raw}


def evaluator_timeout() -> dict:
    return {"error": "evaluator_timeout"}


def internal_error(message: str) -> dict:
    return {"error": "internal_error", "message": message}
