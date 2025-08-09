// Demo microbenchmarks using run-time sizes (powers of two) and typed variants
// (float, double, int). Names are of the form: BM_AddVectorsT/<type>/<size>.

#include <benchmark/benchmark.h>
#include <array>
#include <vector>
#include <algorithm>
#include <numeric>
#include <type_traits>

// (No runtime type-name helpers needed; we rely on BENCHMARK_TEMPLATE to encode type)

// --------------------------------
// Run-time sized add (typed by T), registered via BENCHMARK_TEMPLATE
// --------------------------------
template <typename T>
static void BM_AddVectorsT(benchmark::State& state) {
  const int n = static_cast<int>(state.range(0));
  std::vector<T> a(static_cast<size_t>(n));
  std::vector<T> b(static_cast<size_t>(n));
  std::vector<T> c(static_cast<size_t>(n));
  if constexpr (std::is_integral_v<T>) {
    for (int i = 0; i < n; ++i) {
      a[static_cast<size_t>(i)] = static_cast<T>(i);
      b[static_cast<size_t>(i)] = static_cast<T>(2 * i);
    }
  } else {
    std::iota(a.begin(), a.end(), static_cast<T>(1));
    std::iota(b.begin(), b.end(), static_cast<T>(2));
  }
  for (auto _ : state) {
    for (int i = 0; i < n; ++i) {
      c[static_cast<size_t>(i)] = a[static_cast<size_t>(i)] + b[static_cast<size_t>(i)];
    }
    benchmark::DoNotOptimize(c);
    benchmark::ClobberMemory();
  }
}

// Names will be BM_AddVectorsT/..; type is provided via template parameter
BENCHMARK_TEMPLATE(BM_AddVectorsT, float)->RangeMultiplier(2)->Range(8, 1 << 20);
BENCHMARK_TEMPLATE(BM_AddVectorsT, double)->RangeMultiplier(2)->Range(8, 1 << 20);
BENCHMARK_TEMPLATE(BM_AddVectorsT, int)->RangeMultiplier(2)->Range(8, 1 << 20);

// -------------------------------
// Memcpy-like test with various sizes
// -------------------------------
template <typename T>
static void BM_MemcpyT(benchmark::State& state) {
  const size_t bytes = static_cast<size_t>(state.range(0));
  const size_t n = std::max<size_t>(1, bytes / sizeof(T));
  std::vector<T> src(n);
  std::vector<T> dst(n);
  for (auto _ : state) {
    std::copy(src.begin(), src.end(), dst.begin());
    benchmark::DoNotOptimize(dst);
    benchmark::ClobberMemory();
  }
  state.SetBytesProcessed(bytes * state.iterations());
}

BENCHMARK_TEMPLATE(BM_MemcpyT, float)->RangeMultiplier(2)->Range(1 << 10, 1 << 24);
BENCHMARK_TEMPLATE(BM_MemcpyT, double)->RangeMultiplier(2)->Range(1 << 10, 1 << 24);
BENCHMARK_TEMPLATE(BM_MemcpyT, int)->RangeMultiplier(2)->Range(1 << 10, 1 << 24);

// --------------------------------
// Static arrays (compile-time size) — size templated
// --------------------------------
template <size_t N>
static void BM_StaticArrayMul(benchmark::State& state) {
  std::array<float, N> a;
  std::array<float, N> b;
  std::array<float, N> c;
  std::iota(a.begin(), a.end(), 1.0f);
  std::iota(b.begin(), b.end(), 2.0f);
  for (auto _ : state) {
    for (size_t i = 0; i < N; ++i) {
      c[i] = a[i] * b[i];
    }
    benchmark::DoNotOptimize(c);
    benchmark::ClobberMemory();
  }
}

BENCHMARK(BM_StaticArrayMul<256>);
BENCHMARK(BM_StaticArrayMul<1024>);
BENCHMARK(BM_StaticArrayMul<4096>);
BENCHMARK(BM_StaticArrayMul<8192>);

// --------------------------------
// Fixed-size benchmarks (single size)
// --------------------------------
static void BM_MulVectorsFixed(benchmark::State& state) {
  const int n = 1 << 16; // 65536 elements (fixed)
  std::vector<float> a(static_cast<size_t>(n));
  std::vector<float> b(static_cast<size_t>(n));
  std::vector<float> c(static_cast<size_t>(n));
  std::iota(a.begin(), a.end(), 1.0f);
  std::iota(b.begin(), b.end(), 2.0f);
  for (auto _ : state) {
    for (int i = 0; i < n; ++i) {
      c[static_cast<size_t>(i)] = a[static_cast<size_t>(i)] * b[static_cast<size_t>(i)];
    }
    benchmark::DoNotOptimize(c);
    benchmark::ClobberMemory();
  }
}

static void BM_DotProductFixed(benchmark::State& state) {
  const int n = 1 << 16; // 65536 elements (fixed)
  std::vector<float> a(static_cast<size_t>(n));
  std::vector<float> b(static_cast<size_t>(n));
  std::iota(a.begin(), a.end(), 1.0f);
  std::iota(b.begin(), b.end(), 2.0f);
  for (auto _ : state) {
    float acc = 0.0f;
    for (int i = 0; i < n; ++i) {
      acc += a[static_cast<size_t>(i)] * b[static_cast<size_t>(i)];
    }
    benchmark::DoNotOptimize(acc);
    benchmark::ClobberMemory();
  }
}

BENCHMARK(BM_MulVectorsFixed);
BENCHMARK(BM_DotProductFixed);

BENCHMARK_MAIN();