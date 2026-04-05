from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, computed_field


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


class Issue(BaseModel):
    severity: Literal["error", "warning", "info"]
    message: str
    location: str


class DimensionResult(BaseModel):
    name: str
    score: float  # 0-100
    issues: list[Issue] = []

    @computed_field
    @property
    def grade(self) -> str:
        return _grade(self.score)


class ScorecardReport(BaseModel):
    api_name: str
    api_version: str
    spec_path: str
    overall_score: float
    dimensions: list[DimensionResult]

    @computed_field
    @property
    def grade(self) -> str:
        return _grade(self.overall_score)
