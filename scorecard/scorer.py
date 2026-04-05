from .models import ScorecardReport
from .dimensions import (
    foundational,
    developer_experience,
    ai_readiness,
    agent_usability,
    security,
    discoverability,
)

# Weights must sum to 1.0
DIMENSION_WEIGHTS = {
    "Foundational Compliance": 0.20,
    "Developer Experience": 0.15,
    "AI-Readiness & Agent Experience": 0.20,
    "Agent Usability": 0.20,
    "Security & Governance": 0.15,
    "AI Discoverability": 0.10,
}

SCORERS = [
    foundational,
    developer_experience,
    ai_readiness,
    agent_usability,
    security,
    discoverability,
]


def run(spec: dict, spec_path: str) -> ScorecardReport:
    info = spec.get("info") or {}
    api_name = info.get("title") or "Unknown API"
    api_version = str(info.get("version") or "unknown")

    dimension_results = [scorer.score(spec) for scorer in SCORERS]

    overall = sum(
        result.score * DIMENSION_WEIGHTS.get(result.name, 1 / len(dimension_results))
        for result in dimension_results
    )

    return ScorecardReport(
        api_name=api_name,
        api_version=api_version,
        spec_path=spec_path,
        overall_score=round(overall, 1),
        dimensions=dimension_results,
    )
