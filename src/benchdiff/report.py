"""
report.py (package)

Presentation and printing helpers for BenchDiff terminal output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .color_utils import (
    ansi,
    pad_ansi,
    colorize_direction,
    colorize_rel_change,
    fit_text,
    colorize_severity_label,
    classify_severity,
)
from .compare import (
    Comparison,
    aggregate_series,
    _regression_magnitude_pct,
    _improvement_magnitude_pct,
)


NAME_COL_WIDTH = 48
METRIC_COL_WIDTH = 16
KERNEL_COL_WIDTH = 48
DIR_COL_WIDTH = 12

TOP_REG_COUNT = 6
TOP_IMP_COUNT = 6

AGGREGATED_TABLE_HEADER = (
    f"{'kernel':{KERNEL_COL_WIDTH}} | {'n':>3} | {'mean':>8} | {'min':>8} | {'max':>8} | "
    f"{'direction':>{DIR_COL_WIDTH}} | {'severity':>8}"
)


def _print_aggregated_header() -> None:
    header = AGGREGATED_TABLE_HEADER
    print(header)
    print("-" * len(header))


def _format_aggregated_cells(
    a: Dict[str, Any], *, thresholds: Dict[str, float], color_enabled: bool
) -> Tuple[str, str, str, str, str]:
    if a["aggregated_direction"] == "regression":
        sev_for_label = (
            a["aggregated_severity"] if isinstance(a["aggregated_severity"], str) else "none"
        )
    elif a["aggregated_direction"] == "improvement":
        mag_pct_disp = abs(a.get("mean_relative_change") or 0.0) * 100.0
        sev_for_label = (
            classify_severity(mag_pct_disp, thresholds)
            if mag_pct_disp >= thresholds["minor_pct"]
            else "none"
        )
    else:
        sev_for_label = "none"

    dir_col = colorize_direction(
        a["aggregated_direction"],
        sev_for_label,
        enabled=color_enabled,
    )
    dir_cell = pad_ansi(dir_col, DIR_COL_WIDTH, align="right")

    mean_cell = pad_ansi(
        colorize_rel_change(
            a["mean_relative_change"], thresholds=thresholds, enabled=color_enabled
        ),
        8,
        align="right",
    )

    if a["count"] > 1:
        min_cell = pad_ansi(
            colorize_rel_change(
                a["min_relative_change"], thresholds=thresholds, enabled=color_enabled
            ),
            8,
            align="right",
        )
        max_cell = pad_ansi(
            colorize_rel_change(
                a["max_relative_change"], thresholds=thresholds, enabled=color_enabled
            ),
            8,
            align="right",
        )
    else:
        na_grey = ansi("90", "NA", enabled=color_enabled)
        min_cell = pad_ansi(na_grey, 8, align="right")
        max_cell = pad_ansi(na_grey, 8, align="right")

    sev_cell = pad_ansi(
        colorize_severity_label(
            a["aggregated_severity"] if isinstance(a.get("aggregated_severity"), str) else "none",
            a["aggregated_direction"],
            enabled=color_enabled,
        ),
        8,
        align="right",
    )

    return mean_cell, min_cell, max_cell, dir_cell, sev_cell


def _print_section(title: str, *, color_enabled: bool, bold_if_no_color: bool = True) -> None:
    print("")
    if color_enabled:
        header = ansi("1;35", title, enabled=True)
    else:
        header = ansi("1", title, enabled=True) if bold_if_no_color else title
    print(header)
    print("-" * len(title))


def print_section(title: str, *, color_enabled: bool, bold_if_no_color: bool = True) -> None:
    _print_section(title, color_enabled=color_enabled, bold_if_no_color=bold_if_no_color)


def print_quick_summary(
    comparisons: List[Comparison], *, color_enabled: bool
) -> None:
    regs = [c for c in comparisons if c.direction == "regression"]
    imps = [c for c in comparisons if c.direction == "improvement"]
    _print_section("Quick Summary", color_enabled=color_enabled)

    total_val = ansi("1", str(len(comparisons)), enabled=color_enabled)
    regs_val = (
        ansi("1;31", str(len(regs)), enabled=color_enabled)
        if len(regs) > 0
        else ansi("1", "0", enabled=color_enabled)
    )
    imps_val = (
        ansi("1;32", str(len(imps)), enabled=color_enabled)
        if len(imps) > 0
        else ansi("1", "0", enabled=color_enabled)
    )
    label_width = max(len("Total compared"), len("Regressions"), len("Improvements"))
    value_width = 8
    table_rule = "-" * (label_width + 3 + value_width)

    def _row(label: str, value: str) -> None:
        print(f"{label.ljust(label_width)} | {pad_ansi(value, value_width, align='right')}")

    print(table_rule)
    _row("Total compared", total_val)
    _row("Regressions", regs_val)
    _row("Improvements", imps_val)
    print(table_rule)


def print_aggregated_top(
    comparisons: List[Comparison], *, thresholds: Dict[str, float], color_enabled: bool
) -> None:
    aggs = aggregate_series(comparisons, thresholds=thresholds)
    _print_section(
        "Aggregated per-kernel (top by mean rel change)", color_enabled=color_enabled
    )
    _print_aggregated_header()
    for a in aggs[:10]:
        mean_cell, min_cell, max_cell, dir_cell, sev_cell = _format_aggregated_cells(
            a, thresholds=thresholds, color_enabled=color_enabled
        )
        print(
            f"{a['kernel']:{KERNEL_COL_WIDTH}} | {a['count']:>3} | {mean_cell} | {min_cell} | {max_cell} | {dir_cell} | {sev_cell}"
        )


def print_aggregated_full(
    comparisons: List[Comparison], *, thresholds: Dict[str, float], color_enabled: bool
) -> None:
    aggs = aggregate_series(comparisons, thresholds=thresholds)
    _print_section(
        "Aggregated per-kernel view (mean/min/max relative change)",
        color_enabled=color_enabled,
    )
    _print_aggregated_header()
    for a in aggs[:30]:
        mean_cell, min_cell, max_cell, dir_cell, sev_cell = _format_aggregated_cells(
            a, thresholds=thresholds, color_enabled=color_enabled
        )
        print(
            f"{a['kernel']:{KERNEL_COL_WIDTH}} | {a['count']:>3} | {mean_cell} | {min_cell} | {max_cell} | {dir_cell} | {sev_cell}"
        )


def print_top_entries(
    comparisons: List[Comparison],
    *,
    thresholds: Dict[str, float],
    color_enabled: bool,
    top_imp: Optional[int] = None,
    show_all: bool = False,
) -> None:
    _print_section("Top entries", color_enabled=color_enabled)
    header = (
        f"{'name':{NAME_COL_WIDTH}} | {'metric':{METRIC_COL_WIDTH}} | {'rel_chg':>8} | "
        f"{'direction':>{DIR_COL_WIDTH}} | {'severity':>8}"
    )
    print(header)
    print("-" * len(header))

    regs = [c for c in comparisons if c.direction == "regression"]
    imps = [c for c in comparisons if c.direction == "improvement"]

    regs_sorted = sorted(regs, key=_regression_magnitude_pct, reverse=True)
    reg_iter = regs_sorted if show_all else regs_sorted[:TOP_REG_COUNT]
    for c in reg_iter:
        rel_cell = pad_ansi(
            colorize_rel_change(c.relative_change, thresholds=thresholds, enabled=color_enabled),
            8,
            align="right",
        )
        mag_pct_disp = abs(c.relative_change or 0.0) * 100.0
        sev_for_dir = (
            classify_severity(mag_pct_disp, thresholds)
            if mag_pct_disp >= thresholds["minor_pct"]
            else "minor"
        )
        dir_colored = colorize_direction(c.direction, sev_for_dir, enabled=color_enabled)
        dir_cell = pad_ansi(dir_colored, DIR_COL_WIDTH, align="right")
        name_cell = fit_text(c.name, NAME_COL_WIDTH)
        metric_cell = fit_text(c.metric, METRIC_COL_WIDTH)
        sev_cell = pad_ansi(
            colorize_severity_label(c.severity, c.direction, enabled=color_enabled),
            8,
            align="right",
        )
        print(
            f"{name_cell:{NAME_COL_WIDTH}} | {metric_cell:{METRIC_COL_WIDTH}} | {rel_cell} | {dir_cell} | {sev_cell}"
        )

    print("-" * len(header))

    n_imp = top_imp if top_imp is not None else TOP_IMP_COUNT
    imp_base = sorted(imps, key=_improvement_magnitude_pct, reverse=True)
    imp_selected = imp_base if show_all else imp_base[:n_imp]
    imp_selected = sorted(
        imp_selected, key=lambda c: (c.relative_change if c.relative_change is not None else 0.0)
    )
    for c in imp_selected:
        rel_cell = pad_ansi(
            colorize_rel_change(c.relative_change, thresholds=thresholds, enabled=color_enabled),
            8,
            align="right",
        )
        mag_pct_disp = abs(c.relative_change or 0.0) * 100.0
        sev_for_dir = (
            classify_severity(mag_pct_disp, thresholds)
            if mag_pct_disp >= thresholds["minor_pct"]
            else "minor"
        )
        dir_colored = colorize_direction(c.direction, sev_for_dir, enabled=color_enabled)
        dir_cell = pad_ansi(dir_colored, DIR_COL_WIDTH, align="right")
        name_cell = fit_text(c.name, NAME_COL_WIDTH)
        metric_cell = fit_text(c.metric, METRIC_COL_WIDTH)
        sev_cell = pad_ansi(
            colorize_severity_label(c.severity, c.direction, enabled=color_enabled),
            8,
            align="right",
        )
        print(
            f"{name_cell:{NAME_COL_WIDTH}} | {metric_cell:{METRIC_COL_WIDTH}} | {rel_cell} | {dir_cell} | {sev_cell}"
        )


__all__ = [
    "NAME_COL_WIDTH",
    "METRIC_COL_WIDTH",
    "KERNEL_COL_WIDTH",
    "DIR_COL_WIDTH",
    "TOP_REG_COUNT",
    "TOP_IMP_COUNT",
    "print_section",
    "print_quick_summary",
    "print_aggregated_top",
    "print_aggregated_full",
    "print_top_entries",
]


