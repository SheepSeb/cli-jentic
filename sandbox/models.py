from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, computed_field


class ProbeIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    message: str


class ProbeResult(BaseModel):
    path: str
    method: str
    status_code: int | None = None
    success: bool
    issues: list[ProbeIssue] = []
    request_url: str
    request_body: Any = None
    response_body: Any = None
    response_time_ms: float | None = None

    @computed_field
    @property
    def label(self) -> str:
        return f"{self.method.upper()} {self.path}"


class SandboxReport(BaseModel):
    api_name: str
    api_version: str
    spec_path: str
    base_url: str
    total_endpoints: int
    results: list[ProbeResult]

    @computed_field
    @property
    def successful(self) -> int:
        return sum(1 for r in self.results if r.success)

    @computed_field
    @property
    def feasibility_score(self) -> float:
        if not self.total_endpoints:
            return 0.0
        return round((self.successful / self.total_endpoints) * 100, 1)
