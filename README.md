# api-scorecard

A CLI tool that scores OpenAPI specs for AI-readiness across 6 dimensions — giving APIs a letter grade and actionable recommendations so they work well with AI agents and LLM tooling.

## Installation

```bash
# With uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

## Usage

### Scorecard

```bash
# Score an OpenAPI spec
api-scorecard score path/to/openapi.yaml

# Output as JSON
api-scorecard score path/to/openapi.yaml --json

# Run against the built-in sample spec to see how scoring works
api-scorecard demo
api-scorecard demo --json
```

### Sandbox

The sandbox spins up a local mock server from your spec and auto-probes every endpoint, reporting a **feasibility score** — how well the spec can actually be exercised by an agent.

```bash
# Start a persistent mock server (press Ctrl+C to stop)
api-scorecard sandbox start path/to/openapi.yaml
api-scorecard sandbox start path/to/openapi.yaml --port 9000

# Probe all endpoints and get a report
api-scorecard sandbox probe path/to/openapi.yaml
api-scorecard sandbox probe path/to/openapi.yaml --json

# Run against the built-in sample spec
api-scorecard sandbox demo
api-scorecard sandbox demo --json
```

The `probe` command:
1. Starts an internal mock server
2. Generates synthetic request payloads and path parameters from the spec's schemas
3. Fires requests at every operation
4. Reports per-endpoint status codes, response times, and any issues found
5. Exits with code `2` if the feasibility score is below 50%

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success / score ≥ threshold |
| `1` | Error reading or parsing the spec |
| `2` | Score below threshold (< 60 for scorecard, < 50% for sandbox) |

## What gets scored

Each spec is evaluated across 6 weighted dimensions:

| Dimension | Weight | What it checks |
|-----------|--------|----------------|
| **Foundational Compliance** | 20% | OpenAPI version, `info` object, paths defined, spec validity |
| **Developer Experience** | 15% | Operation IDs, summaries, request/response examples, parameter descriptions |
| **AI-Readiness & Agent Experience** | 20% | Meaningful descriptions, error responses (4xx/5xx), response schemas, schema property descriptions |
| **Agent Usability** | 20% | Semantic operation IDs, tag usage, parameter schemas, request body documentation |
| **Security & Governance** | 15% | Security schemes defined, operations secured, auth documentation |
| **AI Discoverability** | 10% | API-level description, tags defined, external docs |

### Grading

| Score | Grade |
|-------|-------|
| 90–100 | A |
| 80–89 | B |
| 70–79 | C |
| 60–69 | D |
| < 60 | F |

## Example output

```
╭─ API AI Readiness Scorecard ──────────────────────────────────╮
│  Task Manager API  v1.0.0                                      │
│  sample_spec.yaml                                              │
│                                                                │
│  Overall Score: 42.3/100  Grade: F                             │
╰────────────────────────────────────────────────────────────────╯

╭──────────────────────────────────┬───────────┬───────┬──────────────────────────┬────────╮
│ Dimension                        │     Score │ Grade │ Progress                 │ Issues │
├──────────────────────────────────┼───────────┼───────┼──────────────────────────┼────────┤
│ Foundational Compliance          │  75.0/100 │     C │ ███████████████░░░░░     │      1 │
│ Developer Experience             │  38.5/100 │     F │ ███████░░░░░░░░░░░░░░    │      3 │
│ AI-Readiness & Agent Experience  │  31.2/100 │     F │ ██████░░░░░░░░░░░░░░░    │      4 │
│ ...                              │       ... │   ... │ ...                      │    ... │
╰──────────────────────────────────┴───────────┴───────┴──────────────────────────┴────────╯

Issues & Recommendations

  AI-Readiness & Agent Experience
    x 4/6 operations lack descriptive intent (need >30 char description)
       paths.*.*.description
    ! 5/6 operations have no documented error responses (4xx/5xx) — agents cannot handle failure gracefully
       paths.*.*.responses
```

## JSON output

Pass `--json` to get a machine-readable report:

```bash
api-scorecard score openapi.yaml --json | jq '.overall_score'
```

```json
{
  "api_name": "Task Manager API",
  "api_version": "1.0.0",
  "spec_path": "openapi.yaml",
  "overall_score": 42.3,
  "grade": "F",
  "dimensions": [
    {
      "name": "Foundational Compliance",
      "score": 75.0,
      "grade": "C",
      "issues": [...]
    }
  ]
}
```

## Development

```bash
# Install with dev dependencies
uv pip install -e .

# Run directly without installing
python main.py score path/to/spec.yaml
```
