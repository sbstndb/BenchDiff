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

Run the demo to generate fresh examples under `demo/output/` and compare them:

- `bash demo/run_demo.sh`
- `python main.py --ref demo/output/baseline.json --cur demo/output/current.json --metric real_time`

License
-------

MIT
