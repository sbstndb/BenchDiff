#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CPP_DIR="$ROOT_DIR/demo/cpp_bench"
BUILD_DIR="$CPP_DIR/build"
OUT_DIR="$ROOT_DIR/demo/output"

mkdir -p "$BUILD_DIR" "$OUT_DIR"

echo "[build] CMake"
cmake -S "$CPP_DIR" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR" --config Release -j

echo "[bench] baseline"
run_bench() {
  local label="$1"
  "$BUILD_DIR/bench_demo" \
    --benchmark_min_time=0.01s \
    --benchmark_out="$OUT_DIR/${label}.json" \
    --benchmark_out_format=json
}
run_bench baseline

echo "[bench] current"
run_bench current

echo "[analyze] BenchDiff"
python "$ROOT_DIR/main.py" \
  --ref "$OUT_DIR/baseline.json" \
  --cur "$OUT_DIR/current.json" \
  --metric real_time

echo "Done. See $OUT_DIR"


