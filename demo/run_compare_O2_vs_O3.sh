#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CPP_DIR="$ROOT_DIR/demo/cpp_bench"
BUILD_O2="$CPP_DIR/build_O2"
BUILD_O3="$CPP_DIR/build_O3"
OUT_DIR="$ROOT_DIR/demo/output"

mkdir -p "$BUILD_O2" "$BUILD_O3" "$OUT_DIR"

cleanup_tmp() {
  rm -f "$OUT_DIR"/*.tmp 2>/dev/null || true
}
trap cleanup_tmp EXIT INT TERM

configure_build() {
  local build_dir="$1"; shift
  local cxxflags_release="$1"; shift
  echo "[configure] $build_dir (CMAKE_CXX_FLAGS_RELEASE='$cxxflags_release')"
  cmake -S "$CPP_DIR" -B "$build_dir" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS_RELEASE="$cxxflags_release"
}

build_target() {
  local build_dir="$1"; shift
  echo "[build] $build_dir"
  cmake --build "$build_dir" --config Release -j
}

run_bench() {
  local build_dir="$1"; shift
  local label="$1"; shift
  echo "[bench] $label"
  local tmp_out="$OUT_DIR/${label}.json.tmp"
  local final_out="$OUT_DIR/${label}.json"
  "$build_dir/bench_demo" \
    --benchmark_min_time=0.05s \
    --benchmark_out="$tmp_out" \
    --benchmark_out_format=json
  # Attente que le fichier apparaisse et soit non vide (max ~5s)
  for i in {1..50}; do
    if [ -s "$tmp_out" ]; then break; fi
    sleep 0.1
  done
  if [ ! -s "$tmp_out" ]; then
    echo "[error] Fichier JSON non créé: $tmp_out" >&2
    exit 1
  fi
  python -c 'import json,sys,io; p=sys.argv[1];
try:
    with io.open(p, "r", encoding="utf-8") as f: json.load(f)
    print("JSON OK:", p)
except Exception as e:
    import os,sys; print("[error] JSON invalide:", p, e, file=sys.stderr); sys.exit(2)
' "$tmp_out"
  mv -f "$tmp_out" "$final_out"
}

# Baseline: -O2 (sans -march/-mtune)
configure_build "$BUILD_O2" "-O2"
build_target "$BUILD_O2"
run_bench "$BUILD_O2" baseline_O2

# Current: -O3 -march=native -mtune=native
configure_build "$BUILD_O3" "-O3 -march=native -mtune=native"
build_target "$BUILD_O3"
run_bench "$BUILD_O3" current_O3_native

echo "[analyze] BenchDiff"
python "$ROOT_DIR/main.py" \
  --ref "$OUT_DIR/baseline_O2.json" \
  --cur "$OUT_DIR/current_O3_native.json" \
  --metric real_time

echo "Done. See $OUT_DIR"


