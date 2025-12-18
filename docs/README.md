# BenchDiff Documentation

Visual performance regression tool for [Google Benchmark](https://github.com/google/benchmark) traces.

## Quick Start

```bash
pip install benchdiff
benchdiff --ref baseline.json --cur current.json
```

## Documentation

| Document | Description |
|----------|-------------|
| [Usage Guide](usage.md) | CLI options and examples |
| [Development](development.md) | Architecture, API, contributing |

## What It Does

Compares two Google Benchmark JSON files and shows:
- **Regressions** (red/yellow) and **improvements** (green)
- **Severity levels**: minor (2%), moderate (5%), major (10%)
- **Per-kernel aggregation** for templated benchmarks

## Sample Output

```
Quick Summary
-------------
Total compared |      105
Regressions    |        8
Improvements   |       67

Top entries
-----------
BM_MemcpyT<int>/262144    | real_time |   +6.74% |   regression | moderate
BM_AddVectorsT<int>/64    | real_time |  -83.55% |  improvement |     none
```

## Links

- [GitHub](https://github.com/sbstndb/BenchDiff)
- [PyPI](https://pypi.org/project/benchdiff/)
