"""
cli.py

Command-line interface wiring for BenchDiff.

Parses arguments, loads JSONs, orchestrates comparison and reporting, and
handles CI gating exit codes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Dict, Optional

from color_utils import should_enable_color
from compare import (
    DEFAULT_THRESHOLDS,
    extract_benchmarks,
    load_json,
    evaluate_ci_gate,
)
from report import (
    print_quick_summary,
    print_aggregated_top,
    print_aggregated_full,
    print_top_entries,
)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Google Benchmark JSON outputs (local summary only)."
    )
    parser.add_argument("--ref", required=True, help="Reference JSON (baseline)")
    parser.add_argument("--cur", required=True, help="Current JSON (to compare)")
    parser.add_argument(
        "--metric",
        required=False,
        help="Preferred metric (real_time, cpu_time, bytes_per_second, items_per_second)",
    )
    parser.add_argument(
        "--benchmark-filter",
        dest="benchmark_filter",
        required=False,
        help=(
            "Regex to select benchmark names (same semantics as Google Benchmark --benchmark_filter)"
        ),
    )
    parser.add_argument(
        "--thresholds",
        required=False,
        help="JSON string to override thresholds (minor_pct, moderate_pct, major_pct)",
    )
    # CI gating options
    parser.add_argument(
        "--ci", action="store_true", help="Enable CI mode (non-zero exit code on gating failure)"
    )
    parser.add_argument(
        "--ci-fail-on",
        dest="ci_fail_on",
        choices=["minor", "moderate", "major"],
        default="major",
        help="Severity threshold that triggers failure (default: major)",
    )
    parser.add_argument(
        "--ci-max-top-reg-pct",
        dest="ci_max_top_reg_pct",
        type=float,
        default=None,
        help="Fail if the worst regression magnitude exceeds this percentage (e.g., 10.0)",
    )
    # Output control (local only)
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="Show only the aggregated per-kernel view (no per-entry top lists)",
    )
    parser.add_argument(
        "--aggregate-top",
        action="store_true",
        help="Display an aggregated per-kernel top section at the start of the summary",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors (or use NO_COLOR=1)",
    )
    parser.add_argument(
        "--top-imp",
        dest="top_imp",
        type=int,
        default=None,
        help="Number of best improvements to show in Top entries (default: 6)",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show absolutely all measurements (all entries), no truncation",
    )
    return parser.parse_args(argv)


def run(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS.copy()
    if args.thresholds:
        try:
            thr_user = json.loads(args.thresholds)
            thresholds.update({k: float(v) for k, v in thr_user.items()})
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Invalid thresholds JSON: {e}", file=sys.stderr)
            return 2

    # Decide whether to enable ANSI colors
    color_enabled = should_enable_color(no_color_flag=args.no_color, stream=sys.stdout)

    ref_json = load_json(args.ref)
    cur_json = load_json(args.cur)

    ref_map = extract_benchmarks(ref_json)
    cur_map = extract_benchmarks(cur_json)

    # Optional filtering by benchmark name (regex)
    if args.benchmark_filter:
        try:
            pattern = re.compile(args.benchmark_filter)
        except re.error as e:
            print(f"Invalid --benchmark-filter regex: {e}", file=sys.stderr)
            return 2
        ref_map = {name: b for name, b in ref_map.items() if pattern.search(name)}
        cur_map = {name: b for name, b in cur_map.items() if pattern.search(name)}

    from compare import compare_maps  # local import to avoid cycles in type checkers

    comparisons = compare_maps(ref_map, cur_map, args.metric, thresholds)

    # Local display: quick summary + aggregated views
    print_quick_summary(comparisons, color_enabled=color_enabled)

    if args.aggregate_top:
        print_aggregated_top(comparisons, thresholds=thresholds, color_enabled=color_enabled)

    if args.aggregate_only:
        print_aggregated_full(comparisons, thresholds=thresholds, color_enabled=color_enabled)
    else:
        print_top_entries(
            comparisons,
            thresholds=thresholds,
            color_enabled=color_enabled,
            top_imp=args.top_imp,
            show_all=args.show_all,
        )
        print_aggregated_full(
            comparisons, thresholds=thresholds, color_enabled=color_enabled
        )

    # CI mode: apply gating rules and return an error code if necessary
    if args.ci:
        gate = evaluate_ci_gate(
            comparisons,
            fail_on_severity=args.ci_fail_on,
            max_top_reg_pct=args.ci_max_top_reg_pct,
        )
        print("")
        print("CI Gate")
        print("-------")
        print(json.dumps(gate, indent=2))
        if gate["failed"]:
            print("CI gating: échec des règles de régression.", file=sys.stderr)
            return 4

    return 0


__all__ = ["parse_args", "run"]


