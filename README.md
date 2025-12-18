BenchDiff
===========

**BenchDiff** is a visual tool for spotting performance regressions and improvements in [Google Benchmark](https://github.com/google/benchmark) traces.

Unlike the `compare.py` script bundled with Google Benchmark, BenchDiff provides:
- **Clear visual output** with severity-based coloring (minor/moderate/major)
- **Per-kernel aggregation** to easily analyze templated benchmarks
- **CI mode** with configurable thresholds and exit codes

![BenchDiff console output](media/screenshot.png)

Install
-------

Requires Python 3.10+

```bash
pip install benchdiff
```

Quick Start
-----------

```bash
# Basic comparison
benchdiff --ref baseline.json --cur current.json

# Aggregated view (per-kernel summary)
benchdiff --ref baseline.json --cur current.json --aggregate-only

# CI mode (exit 4 on major regression)
benchdiff --ref baseline.json --cur current.json --ci --ci-fail-on major
```

Try with included sample data:

```bash
benchdiff --ref demo/baseline_O2.json --cur demo/current_O3_native.json
```

Documentation
-------------

See the [docs](docs/) folder for detailed documentation:

- [Usage Guide](docs/usage.md) — CLI options and examples
- [Development](docs/development.md) — Architecture, API, contributing

License
-------

BSD 3-Clause
