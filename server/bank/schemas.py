"""Pydantic schemas for bank/generated/<slug>.json files.

Strict by design: catches generation drift (wrong field name, missing hints,
gap in step ordinals) before validation/ingest spends real time."""
from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class HintJSON(BaseModel):
    level: Literal[1, 2, 3]
    text: str = Field(min_length=1)


class StepJSON(BaseModel):
    ordinal: int = Field(ge=1)
    description: str = Field(min_length=10)
    pattern_tags: list[str] = Field(default_factory=list)
    hints: list[HintJSON]

    @model_validator(mode="after")
    def _hints_exactly_three_levels(self):
        levels = sorted(h.level for h in self.hints)
        if levels != [1, 2, 3]:
            raise ValueError(
                f"step {self.ordinal} must have exactly 3 hints at levels [1,2,3], got {levels}"
            )
        return self


class CanonicalSolution(BaseModel):
    language: Literal["python"]
    code: str = Field(min_length=10)
    time: str
    space: str


class TestCase(BaseModel):
    # Pydantic class, not a pytest test class.
    __test__ = False

    # `input` is the positional-args list passed to the canonical solution
    # via *args. Empty list would mean fn() with no args, which doesn't fit
    # any LeetCode-style problem - reject at schema time for a clearer error
    # than the eventual TypeError from the runner.
    input: list = Field(min_length=1)
    expected: object


class QuestionJSON(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    statement: str = Field(min_length=20)
    difficulty: Literal["easy", "medium", "hard"]
    leetcode_id: int | None = None
    topics: list[str] = Field(min_length=1)
    canonical_solution: CanonicalSolution
    test_cases: list[TestCase] = Field(min_length=3)
    steps: list[StepJSON] = Field(min_length=3, max_length=10)

    @model_validator(mode="after")
    def _step_ordinals_dense_from_one(self):
        ords = [s.ordinal for s in self.steps]
        expected = list(range(1, len(self.steps) + 1))
        if ords != expected:
            raise ValueError(f"step ordinals must be dense and 1-based, got {ords}")
        return self
