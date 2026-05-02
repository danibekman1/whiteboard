"""Structured tool error builders.

Each helper returns a JSON-serializable dict with an `error` discriminator
and per-variant fields. These cross the MCP boundary verbatim and are
parsed by the web client by checking `result.error`.
"""
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
