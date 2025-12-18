# Development

## Project Structure

```
src/benchdiff/
├── cli.py          # CLI (argparse, orchestration)
├── compare.py      # Core logic (comparison, aggregation, CI gate)
├── report.py       # Terminal output (tables, formatting)
└── color_utils.py  # ANSI colors
```

## Architecture

```
JSON files → extract_benchmarks() → compare_maps() → List[Comparison] → print functions
```

**Key data structures:**
- `Comparison`: name, metric, ref/cur values, pct_change, direction, severity
- Direction: `regression`, `improvement`, `unchanged`
- Severity: `minor`, `moderate`, `major`, `none`

## Python API

```python
from benchdiff.compare import (
    load_json, extract_benchmarks, compare_maps,
    evaluate_ci_gate, DEFAULT_THRESHOLDS
)

ref = extract_benchmarks(load_json("baseline.json"))
cur = extract_benchmarks(load_json("current.json"))
comparisons = compare_maps(ref, cur, "real_time", DEFAULT_THRESHOLDS)

for c in comparisons:
    if c.direction == "regression":
        print(f"{c.name}: {c.pct_change:+.2f}%")

# CI check
gate = evaluate_ci_gate(comparisons, fail_on_severity="major")
if gate["failed"]:
    print(gate["reasons"])
```

## Contributing

```bash
git clone https://github.com/sbstndb/BenchDiff.git
cd BenchDiff
pip install -e .
```

**Dependencies:** Python 3.10+ (stdlib only)

**Code style:** Standard Python conventions

**License:** BSD 3-Clause
