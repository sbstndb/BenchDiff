BenchDiff
===========

![Aperçu de la sortie console de BenchDiff](media/screenshot.png)

 Ultra-concise performance regression reporting for Google Benchmark traces (local summary only).

- Input: two JSON traces (reference vs current)
- Output: terse regression analysis (bullets + compact JSON) and a small local summary
- Use-cases: PR gating, CI checks, quick diagnosis of perf drifts

Features
--------

- Auto-metric pick: `real_time`, `cpu_time`, `bytes_per_second`, `items_per_second`
- Regression classification (minor/moderate/major) with configurable thresholds
- Local terminal summary with ANSI colors
- CI mode (`--ci`) with fail-on-severity and max-top-regression limits

Install
-------

- Python 3.10+

Usage
-----

- Basic:
  - `python main.py --ref baseline.json --cur current.json --metric real_time`
- CI gate:
  - `python main.py --ref baseline.json --cur current.json --metric real_time --ci --ci-fail-on major --ci-max-top-reg-pct 10`
- Filter benchmarks by name (regex, similar to Google Benchmark `--benchmark_filter`):
  - `python main.py --ref baseline.json --cur current.json --benchmark-filter "^BM_AddVectorsT<.*>/[0-9]+$"`

Demo (C++ microbenchmarks)
--------------------------

A minimal Google Benchmark demo is under `demo/cpp_bench`.

- Build:
  - `cmake -S demo/cpp_bench -B demo/cpp_bench/build -DCMAKE_BUILD_TYPE=Release`
  - `cmake --build demo/cpp_bench/build -j`

- Produce traces:
  - `mkdir -p demo/output`
  - `demo/cpp_bench/build/bench_demo --benchmark_out=demo/output/baseline.json --benchmark_out_format=json`
  - `demo/cpp_bench/build/bench_demo --benchmark_out=demo/output/current.json  --benchmark_out_format=json`

- Analyze:
  - `python main.py --ref demo/output/baseline.json --cur demo/output/current.json --metric real_time`

Project structure
-----------------

The project was refactored into three focused modules:

- `compare.py`: core comparison logic and CI gating
- `report.py`: terminal rendering (colors, tables, sections)
- `cli.py`: argument parsing and orchestration

The entry point `main.py` remains for backward-compatibility and delegates to `cli.py`.

Example output
--------------

Short excerpt of the local terminal summary:

```text
--- Quick Summary ---
Total compared: 105  |  Regressions: 43  |  Improvements: 37

Aggregated per-kernel (top by mean rel change):
kernel                                                       |   n |     mean |      min |      max |          dir |      sev
...
```

Naive diff (for comparison)
---------------------------

A simple unified diff between the raw Google Benchmark JSON files is noisy and hard to act on:

```diff
--- demo/output/baseline.json
+++ demo/output/current.json
@@ "benchmarks"[1]
-  "name": "BM_AddVectors_Large/65536",
-  "real_time": 6239.286587,
+  "name": "BM_AddVectors_Large/65536",
+  "real_time": 7893.413373,
   "time_unit": "ns"
@@ "benchmarks"[2]
-  "name": "BM_Memcpy_Chunked/1048576",
-  "bytes_per_second": 4.3174002757e+10
+  "name": "BM_Memcpy_Chunked/1048576",
+  "bytes_per_second": 4.1833883170e+10
```

BenchDiff surfaces direction, relative change, severity, and CI checks in a compact, actionable form.

License
-------

MIT
