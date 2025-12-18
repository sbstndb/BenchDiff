# Usage Guide

## Basic Usage

```bash
benchdiff --ref baseline.json --cur current.json --metric real_time
```

## Options

### Required
| Option | Description |
|--------|-------------|
| `--ref <file>` | Baseline JSON file |
| `--cur <file>` | Current JSON file |

### Metric Selection
| Option | Description |
|--------|-------------|
| `--metric <name>` | `real_time`, `cpu_time`, `bytes_per_second`, `items_per_second` |

### Filtering & Display
| Option | Description |
|--------|-------------|
| `--benchmark-filter <regex>` | Filter benchmarks by name |
| `--aggregate-only` | Show only per-kernel summary |
| `--show-all` | Show all entries (no truncation) |
| `--no-color` | Disable colors |

### Thresholds
| Option | Description |
|--------|-------------|
| `--thresholds <json>` | Custom thresholds (default: minor=2%, moderate=5%, major=10%) |

Example:
```bash
--thresholds '{"minor_pct": 1.0, "moderate_pct": 3.0, "major_pct": 5.0}'
```

### CI Mode
| Option | Description |
|--------|-------------|
| `--ci` | Enable CI mode (exit code 4 on failure) |
| `--ci-fail-on <level>` | `minor`, `moderate`, or `major` (default: major) |
| `--ci-max-top-reg-pct <n>` | Fail if worst regression exceeds n% |

## Examples

```bash
# Basic comparison
benchdiff --ref baseline.json --cur current.json

# Only show aggregated per-kernel view
benchdiff --ref baseline.json --cur current.json --aggregate-only

# Filter specific benchmarks
benchdiff --ref baseline.json --cur current.json --benchmark-filter "BM_Add.*"

# CI pipeline (fail on moderate+ regressions)
benchdiff --ref baseline.json --cur current.json --ci --ci-fail-on moderate

# Stricter thresholds
benchdiff --ref baseline.json --cur current.json \
  --thresholds '{"minor_pct": 1.0, "moderate_pct": 2.0, "major_pct": 5.0}'
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Input error |
| 4 | CI gate failed |

## CI Integration (GitHub Actions)

```yaml
- name: Check regressions
  run: |
    pip install benchdiff
    benchdiff --ref baseline.json --cur current.json --ci --ci-fail-on moderate
```
