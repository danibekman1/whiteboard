"""Pydantic schemas for bank/seed/sd_curated/<slug>.json and bank/generated/<sd-slug>.json.

Strict by design: catches generation drift (wrong phase order, missing
checklists, too few pushbacks) before validation/ingest spends real time.
Mirrors bank/schemas.py for the algo path."""
from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Phase = Literal["clarify", "estimate", "high_level", "deep_dive", "tradeoffs"]
PHASES_REQUIRED: tuple[Phase, ...] = ("clarify", "estimate", "high_level", "deep_dive", "tradeoffs")


class ChecklistItemJSON(BaseModel):
    item: str = Field(min_length=10)
    required: bool = True


class PhaseJSON(BaseModel):
    phase: Phase
    ordinal: int = Field(ge=1, le=5)
    checklist: list[ChecklistItemJSON] = Field(min_length=3, max_length=8)


class PushbackJSON(BaseModel):
    trigger_tag: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    trigger_desc: str = Field(min_length=20)
    response: str = Field(min_length=20)


class SDQuestionJSON(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    type: Literal["system_design"]
    title: str = Field(min_length=1)
    statement: str = Field(min_length=40)
    difficulty: Literal["easy", "medium", "hard"]
    scenario_tag: str = Field(min_length=3)
    phases: list[PhaseJSON] = Field(min_length=5, max_length=5)
    pushbacks: list[PushbackJSON] = Field(min_length=3, max_length=10)

    @model_validator(mode="after")
    def _phases_complete_and_ordered(self):
        names = tuple(p.phase for p in self.phases)
        if names != PHASES_REQUIRED:
            raise ValueError(
                f"phases must be exactly {PHASES_REQUIRED} in order, got {names}"
            )
        ords = [p.ordinal for p in self.phases]
        if ords != [1, 2, 3, 4, 5]:
            raise ValueError(f"phase ordinals must be 1..5 in order, got {ords}")
        return self
