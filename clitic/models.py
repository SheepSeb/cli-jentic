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
    location: str  # e.g. "--help", "exit_code", "stderr"


class DimensionResult(BaseModel):
    name: str
    score: float  # 0–100
    issues: list[Issue] = []

    @computed_field
    @property
    def grade(self) -> str:
        return _grade(self.score)


class CLIToolReport(BaseModel):
    tool_name: str
    tool_path: str  # resolved path or "not found"
    overall_score: float
    dimensions: list[DimensionResult]

    @computed_field
    @property
    def grade(self) -> str:
        return _grade(self.overall_score)
