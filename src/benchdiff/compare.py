"""
compare.py (package)

Core comparison logic and data structures for BenchDiff.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from .color_utils import classify_severity


DEFAULT_THRESHOLDS: Dict[str, float] = {
    "minor_pct": 2.0,
    "moderate_pct": 5.0,
    "major_pct": 10.0,
}

THROUGHPUT_METRICS = {"bytes_per_second", "items_per_second"}


@dataclass
class BenchEntry:
    name: str
    metric: str
    value: float
    time_unit: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class Comparison:
    name: str
    metric: str
    ref_value: float
    cur_value: float
    pct_change: Optional[float]
    direction: str
    severity: str
    time_unit: Optional[str]
    notes: Optional[str]
    relative_change: Optional[float] = None


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_benchmarks(json_obj: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    arr = (
        json_obj.get("benchmarks")
        if isinstance(json_obj, dict) and isinstance(json_obj.get("benchmarks"), list)
        else json_obj if isinstance(json_obj, list) else None
    )
    if arr is None:
        raise ValueError("Input JSON doesn't contain 'benchmarks' list. Provide the JSON produced by Google Benchmark.")

    def _name(b: Dict[str, Any]) -> Optional[str]:
        return b.get("name") or b.get("benchmark") or b.get("bench")

    return {n: b for b in arr if (n := _name(b))}


def choose_metric_for_benchmark(
    bench_obj: Dict[str, Any], prefer: Optional[str] = None
) -> Tuple[str, Optional[str], float]:
    time_unit = bench_obj.get("time_unit")
    candidates = ([prefer] if prefer else []) + [
        "real_time",
        "cpu_time",
        "bytes_per_second",
        "items_per_second",
    ]
    for key in candidates:
        if key and key in bench_obj:
            return key, time_unit, float(bench_obj[key])
    pm = bench_obj.get("primary_metric") or bench_obj.get("primary")
    if isinstance(pm, dict):
        for key in ("value", "real_time", "cpu_time"):
            if key in pm:
                return key, time_unit, float(pm[key])
    raise ValueError(f"Could not find a known metric in benchmark {bench_obj.get('name')}")


def compare_maps(
    ref_map: Dict[str, Dict[str, Any]],
    cur_map: Dict[str, Dict[str, Any]],
    metric_preference: Optional[str],
    thresholds: Dict[str, float],
) -> List[Comparison]:
    out: List[Comparison] = []
    names = sorted(set(ref_map.keys()) & set(cur_map.keys()))
    for name in names:
        ref = ref_map[name]
        cur = cur_map[name]
        try:
            metric_field_ref, time_unit_ref, ref_val = choose_metric_for_benchmark(
                ref, metric_preference
            )
            _metric_field_cur, time_unit_cur, cur_val = choose_metric_for_benchmark(
                cur, metric_preference
            )
        except ValueError as e:
            out.append(
                Comparison(
                    name,
                    metric_preference or "unknown",
                    math.nan,
                    math.nan,
                    None,
                    "unknown",
                    "none",
                    None,
                    f"metric error: {e}",
                )
            )
            continue

        metric_field = metric_field_ref

        if ref_val == 0:
            pct = None
            notes = "ref value is zero (cannot compute pct change)"
        else:
            pct = (cur_val - ref_val) / abs(ref_val) * 100.0
            notes = None

        def _direction_and_severity(metric_field: str, pct: Optional[float]) -> Tuple[str, str]:
            if pct is None:
                return "unknown", "none"
            sign = -1 if metric_field in THROUGHPUT_METRICS else 1
            signed_pct = sign * pct
            if signed_pct > thresholds["minor_pct"]:
                return "regression", classify_severity(signed_pct, thresholds)
            if signed_pct < -thresholds["minor_pct"]:
                return "improvement", "none"
            return "unchanged", "none"

        direction, severity = _direction_and_severity(metric_field, pct)

        out.append(
            Comparison(
                name=name,
                metric=metric_field,
                ref_value=ref_val,
                cur_value=cur_val,
                pct_change=round(pct, 4) if pct is not None else None,
                relative_change=round(pct / 100.0, 6) if pct is not None else None,
                direction=direction,
                severity=severity,
                time_unit=time_unit_ref or time_unit_cur,
                notes=notes,
            )
        )
    return sorted(
        out,
        key=lambda c: (c.direction != "regression", -(c.pct_change or 0) if c.pct_change else 0),
    )


def _split_kernel_and_size(bench_name: str) -> Tuple[str, Optional[int]]:
    if "/" in bench_name:
        base, maybe_size = bench_name.rsplit("/", 1)
        if maybe_size.isdigit():
            return base, int(maybe_size)
        return base, None
    return bench_name, None


def aggregate_series(
    comparisons: List[Comparison], *, thresholds: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    groups: Dict[str, List[Comparison]] = {}
    for c in comparisons:
        key, _ = _split_kernel_and_size(c.name)
        groups.setdefault(key, []).append(c)

    aggregates: List[Dict[str, Any]] = []
    for key, entries in groups.items():
        rels = [e.relative_change for e in entries if e.relative_change is not None]
        if not rels:
            continue
        mean_rc = statistics.fmean(rels)
        min_rc, max_rc = min(rels), max(rels)
        mag_pct = abs(mean_rc) * 100.0
        if mag_pct < thresholds["minor_pct"]:
            aggregated_direction = "unchanged"
        else:
            aggregated_direction = "regression" if mean_rc > 0 else "improvement"
        agg_sev = (
            classify_severity(mag_pct, thresholds) if aggregated_direction == "regression" else "none"
        )
        aggregates.append(
            {
                "kernel": key,
                "count": len(entries),
                "mean_relative_change": round(mean_rc, 6),
                "min_relative_change": round(min_rc, 6),
                "max_relative_change": round(max_rc, 6),
                "aggregated_direction": aggregated_direction,
                "aggregated_severity": agg_sev,
            }
        )
    return sorted(aggregates, key=lambda x: x["mean_relative_change"], reverse=True)


def _regression_magnitude_pct(c: Comparison) -> float:
    if c.direction != "regression" or c.pct_change is None:
        return 0.0
    return max(0.0, -c.pct_change) if c.metric in THROUGHPUT_METRICS else max(0.0, c.pct_change)


def _improvement_magnitude_pct(c: Comparison) -> float:
    if c.direction != "improvement" or c.pct_change is None:
        return 0.0
    return max(0.0, c.pct_change) if c.metric in THROUGHPUT_METRICS else max(0.0, -c.pct_change)


def evaluate_ci_gate(
    comparisons: List[Comparison],
    fail_on_severity: str = "major",
    max_top_reg_pct: Optional[float] = None,
) -> Dict[str, Any]:
    severity_rank = {"none": 0, "minor": 1, "moderate": 2, "major": 3}
    threshold_rank = severity_rank.get(fail_on_severity, 3)

    regressions = [c for c in comparisons if c.direction == "regression"]
    worst, worst_mag = None, 0.0
    reasons: List[str] = []
    for c in regressions:
        mag = _regression_magnitude_pct(c)
        if mag >= worst_mag:
            worst_mag, worst = mag, c
        if severity_rank.get(c.severity, 0) >= threshold_rank:
            reasons.append(
                f"severity>={fail_on_severity}: {c.name} ({c.metric}) {c.pct_change:+.2f}%"
            )

    if max_top_reg_pct is not None and worst_mag >= max_top_reg_pct:
        if worst is not None:
            reasons.append(
                f"top_regression {worst.name} ({worst.metric}) magnitude {worst_mag:.2f}% >= {max_top_reg_pct:.2f}%"
            )
        else:
            reasons.append(
                f"top_regression magnitude {worst_mag:.2f}% >= {max_top_reg_pct:.2f}%"
            )

    return {
        "failed": len(reasons) > 0,
        "reasons": reasons,
        "worst_regression": asdict(worst) if worst is not None else None,
    }


__all__ = [
    "DEFAULT_THRESHOLDS",
    "THROUGHPUT_METRICS",
    "BenchEntry",
    "Comparison",
    "load_json",
    "extract_benchmarks",
    "choose_metric_for_benchmark",
    "compare_maps",
    "aggregate_series",
    "_regression_magnitude_pct",
    "_improvement_magnitude_pct",
    "evaluate_ci_gate",
]


