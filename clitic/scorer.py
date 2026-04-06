from .models import CLIToolReport
from .analyzer import ToolProbe
from .dimensions import discoverability, output_format, exit_codes, error_handling, arg_design

# Weights must sum to 1.0
DIMENSION_WEIGHTS = {
    "Help & Discoverability": 0.25,
    "Machine-Readable Output": 0.25,
    "Exit Code Semantics": 0.20,
    "Error Handling": 0.15,
    "Argument & Interface Design": 0.15,
}

SCORERS = [
    discoverability,
    output_format,
    exit_codes,
    error_handling,
    arg_design,
]


def run(probe: ToolProbe) -> CLIToolReport:
    dimension_results = [scorer.score(probe) for scorer in SCORERS]

    overall = sum(
        result.score * DIMENSION_WEIGHTS.get(result.name, 1 / len(dimension_results))
        for result in dimension_results
    )

    return CLIToolReport(
        tool_name=probe.tool_name,
        tool_path=probe.tool_path or "not found",
        overall_score=round(overall, 1),
        dimensions=dimension_results,
    )
