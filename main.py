#!/usr/bin/env python3
"""
main.py

Comparateur de traces Google Benchmark avec résumé local.

Usage:
    python main.py --ref ref.json --cur cur.json
Options:
    --metric METRIC       Metric to compare (real_time, cpu_time, bytes_per_second, items_per_second).
    --thresholds JSON     Optional JSON string to override thresholds.
"""

import sys
import json
import math
import argparse
import re
import statistics
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from color_utils import (
    ansi,
    pad_ansi,
    colorize_direction,
    colorize_rel_change,
    fit_text,
    should_enable_color,
    colorize_severity_label,
    classify_severity,
)
# Exceptions spécifiques (tout est local)

# -------------------------
# Configuration / thresholds
# -------------------------
DEFAULT_THRESHOLDS = {
    # For time-like metrics: percent increase means slower (bad).
    # For throughput-like metrics: percent decrease is bad.
    "minor_pct": 2.0,    # >= 2% considered worth flagging
    "moderate_pct": 5.0,
    "major_pct": 10.0
}

# Metrics where larger is better (decrease is a regression)
THROUGHPUT_METRICS = {"bytes_per_second", "items_per_second"}


# -------------------------
# Data structures
# -------------------------
@dataclass
class BenchEntry:
    name: str
    metric: str  # which field we use, e.g. "real_time"
    value: float
    time_unit: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class Comparison:
    name: str
    metric: str
    ref_value: float
    cur_value: float
    pct_change: Optional[float]  # positive = increase ((cur-ref)/ref *100)
    direction: str  # "regression"|"improvement"|"unchanged"
    severity: str  # none/minor/moderate/major
    time_unit: Optional[str]
    notes: Optional[str]
    # unit-less fraction: +0.5 == +50%
    relative_change: Optional[float] = None


# -------------------------
# Helpers: load & parse
# -------------------------
def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_benchmarks(json_obj: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Retourne un mapping name->benchmark depuis un JSON Google Benchmark (ou liste)."""
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


def choose_metric_for_benchmark(bench_obj: Dict[str, Any], prefer: Optional[str] = None) -> Tuple[str, Optional[str], float]:
    """Retourne (metric_field, time_unit, value) en respectant une préférence éventuelle."""
    time_unit = bench_obj.get("time_unit")
    candidates = ([prefer] if prefer else []) + ["real_time", "cpu_time", "bytes_per_second", "items_per_second"]
    for key in candidates:
        if key and key in bench_obj:
            return key, time_unit, float(bench_obj[key])
    pm = bench_obj.get("primary_metric") or bench_obj.get("primary")
    if isinstance(pm, dict):
        for key in ("value", "real_time", "cpu_time"):
            if key in pm:
                return key, time_unit, float(pm[key])
    raise ValueError(f"Could not find a known metric in benchmark {bench_obj.get('name')}")


# -------------------------
# Comparison logic
# -------------------------
def compare_maps(ref_map: Dict[str, Dict[str, Any]],
                 cur_map: Dict[str, Dict[str, Any]],
                 metric_preference: Optional[str],
                 thresholds: Dict[str, float]) -> List[Comparison]:
    out: List[Comparison] = []
    names = sorted(set(ref_map.keys()) & set(cur_map.keys()))
    for name in names:
        ref = ref_map[name]
        cur = cur_map[name]
        try:
            metric_field_ref, time_unit_ref, ref_val = choose_metric_for_benchmark(ref, metric_preference)
            _metric_field_cur, time_unit_cur, cur_val = choose_metric_for_benchmark(cur, metric_preference)
        except ValueError as e:
            # skip if metric missing
            out.append(Comparison(name, metric_preference or "unknown", math.nan, math.nan, None, "unknown", "none", None, f"metric error: {e}"))
            continue
        # If fields differ, pick the chosen metric_field_ref (should match)
        metric_field = metric_field_ref
        # Compute percent change relative to reference
        if ref_val == 0:
            pct = None
            notes = "ref value is zero (cannot compute pct change)"
        else:
            pct = (cur_val - ref_val) / abs(ref_val) * 100.0
            notes = None
        # Determine direction & severity (temps: hausse = régression; débit: baisse = régression)
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
        # no separate performance_change kept; direction + relative_change are sufficient

        out.append(Comparison(
            name=name,
            metric=metric_field,
            ref_value=ref_val,
            cur_value=cur_val,
            pct_change=round(pct, 4) if pct is not None else None,
            relative_change=round(pct / 100.0, 6) if pct is not None else None,
            direction=direction,
            severity=severity,
            time_unit=time_unit_ref or time_unit_cur,
            notes=notes
        ))
    return sorted(out, key=lambda c: (c.direction != "regression", -(c.pct_change or 0) if c.pct_change else 0))

# -------------------------
# Color helpers (delegation vers color_utils)
# -------------------------


# (Plus de génération de prompt — tout est local)





# -------------------------
# Aggregation across size-series
# -------------------------
def _split_kernel_and_size(bench_name: str) -> Tuple[str, Optional[int]]:
    # Expect names like "BM_AddVectorsT<float>/1024" or "BM_AddVectorsT<int>/32"
    if '/' in bench_name:
        base, maybe_size = bench_name.rsplit('/', 1)
        if maybe_size.isdigit():
            return base, int(maybe_size)
        return base, None
    return bench_name, None


def aggregate_series(comparisons: List[Comparison], *, thresholds: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    groups: Dict[str, List[Comparison]] = defaultdict(list)
    for c in comparisons:
        key, _ = _split_kernel_and_size(c.name)
        groups[key].append(c)

    aggregates: List[Dict[str, Any]] = []
    for key, entries in groups.items():
        rels = [e.relative_change for e in entries if e.relative_change is not None]
        if not rels:
            continue
        mean_rc = statistics.fmean(rels)
        min_rc, max_rc = min(rels), max(rels)
        mag_pct = abs(mean_rc) * 100.0
        # Neutral band: consider 'unchanged' if within minor threshold
        if mag_pct < thresholds["minor_pct"]:
            aggregated_direction = "unchanged"
        else:
            aggregated_direction = "regression" if mean_rc > 0 else "improvement"
        agg_sev = classify_severity(mag_pct, thresholds) if aggregated_direction == "regression" else "none"
        aggregates.append({
            "kernel": key,
            "count": len(entries),
            "mean_relative_change": round(mean_rc, 6),
            "min_relative_change": round(min_rc, 6),
            "max_relative_change": round(max_rc, 6),
            "aggregated_direction": aggregated_direction,
            "aggregated_severity": agg_sev,
        })
    # Trier du moins favorable au plus favorable selon le mean (positif = régression, négatif = amélioration)
    return sorted(aggregates, key=lambda x: x["mean_relative_change"], reverse=True)

# -------------------------
# CI gating
# -------------------------
def _regression_magnitude_pct(c: Comparison) -> float:
    """Retourne l'ampleur positive de la régression en pourcentage (0 si non applicable)."""
    if c.direction != "regression" or c.pct_change is None:
        return 0.0
    return max(0.0, -c.pct_change) if c.metric in THROUGHPUT_METRICS else max(0.0, c.pct_change)


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
            reasons.append(f"severité>={fail_on_severity}: {c.name} ({c.metric}) {c.pct_change:+.2f}%")

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


def _improvement_magnitude_pct(c: Comparison) -> float:
    """Amplitude positive d'une amélioration en pourcentage (0 si NA)."""
    if c.direction != "improvement" or c.pct_change is None:
        return 0.0
    # time-like: amélioration => pct négatif -> magnitude positive = -pct
    # throughput: amélioration => pct positif -> magnitude positive = pct
    return max(0.0, c.pct_change) if c.metric in THROUGHPUT_METRICS else max(0.0, -c.pct_change)


# -------------------------
# Printing helpers (reduce duplication)
# -------------------------

# Colonnes plus compactes pour écrans étroits (moitié d'écran)
NAME_COL_WIDTH = 48
METRIC_COL_WIDTH = 16
KERNEL_COL_WIDTH = 48
DIR_COL_WIDTH = 12
# Tailles des listes Top
TOP_REG_COUNT = 6
TOP_IMP_COUNT = 6

AGGREGATED_TABLE_HEADER = (
    f"{'kernel':{KERNEL_COL_WIDTH}} | {'n':>3} | {'mean':>8} | {'min':>8} | {'max':>8} | "
    f"{'direction':>{DIR_COL_WIDTH}} | {'severity':>8}"
)

def _print_aggregated_header() -> None:
    aheader = AGGREGATED_TABLE_HEADER
    print(aheader)
    print("-" * len(aheader))


def _format_aggregated_cells(a: Dict[str, Any], *, thresholds: Dict[str, float], color_enabled: bool) -> Tuple[str, str, str, str, str]:
    """Retourne (mean_cell, min_cell, max_cell, dir_cell, sev_cell) formatés/paddés.

    Ne gère pas la cellule du nom de kernel (format variable selon le contexte d'appel).
    """
    # Harmoniser la sévérité d'affichage pour les deux directions
    if a["aggregated_direction"] == "regression":
        sev_for_label = a["aggregated_severity"] if isinstance(a["aggregated_severity"], str) else "none"
    elif a["aggregated_direction"] == "improvement":
        mag_pct_disp = abs(a.get("mean_relative_change") or 0.0) * 100.0
        sev_for_label = classify_severity(mag_pct_disp, thresholds) if mag_pct_disp >= thresholds["minor_pct"] else "none"
    else:
        sev_for_label = "none"
    dir_col = colorize_direction(
        a["aggregated_direction"],
        sev_for_label,
        enabled=color_enabled,
    )
    dir_cell = pad_ansi(dir_col, DIR_COL_WIDTH, align="right")

    mean_cell = pad_ansi(
        colorize_rel_change(a["mean_relative_change"], thresholds=thresholds, enabled=color_enabled),
        8,
        align="right",
    )

    if a["count"] > 1:
        min_cell = pad_ansi(
            colorize_rel_change(a["min_relative_change"], thresholds=thresholds, enabled=color_enabled),
            8,
            align="right",
        )
        max_cell = pad_ansi(
            colorize_rel_change(a["max_relative_change"], thresholds=thresholds, enabled=color_enabled),
            8,
            align="right",
        )
    else:
        na_grey = ansi("90", "NA", enabled=color_enabled)
        min_cell = pad_ansi(na_grey, 8, align="right")
        max_cell = pad_ansi(na_grey, 8, align="right")

    sev_cell = pad_ansi(
        colorize_severity_label(
            a["aggregated_severity"] if isinstance(a["aggregated_severity"], str) else "none",
            a["aggregated_direction"],
            enabled=color_enabled,
        ),
        8,
        align="right",
    )

    return mean_cell, min_cell, max_cell, dir_cell, sev_cell






# Helpers de section (lisibilité)
def _print_section(title: str, *, color_enabled: bool, bold_if_no_color: bool = True) -> None:
    """Affiche un titre de section distinctif.

    - Couleur par défaut: magenta vif + gras
    - Si les couleurs sont désactivées, on garde le gras pour distinguer
    """
    print("")
    if color_enabled:
        header = ansi("1;35", title, enabled=True)
    else:
        header = ansi("1", title, enabled=True) if bold_if_no_color else title
    print(header)
    # La règle doit matcher la longueur visible du titre, pas les codes ANSI
    print("-" * len(title))



# -------------------------
# CLI & main
# -------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Compare Google Benchmark JSON outputs (local summary only).")
    p.add_argument("--ref", required=True, help="Reference JSON (baseline)")
    p.add_argument("--cur", required=True, help="Current JSON (to compare)")
    p.add_argument("--metric", required=False, help="Preferred metric (real_time, cpu_time, bytes_per_second, items_per_second)")
    p.add_argument("--benchmark-filter", dest="benchmark_filter", required=False,
                   help="Regex pour sélectionner des benchmarks (mêmes principes que --benchmark_filter de Google Benchmark)")
    p.add_argument("--thresholds", required=False, help="JSON string to override thresholds (minor_pct, moderate_pct, major_pct)")
    # CI gating options
    p.add_argument("--ci", action="store_true", help="Activer mode CI (exit code non-zero si gating échoue)")
    p.add_argument("--ci-fail-on", dest="ci_fail_on", choices=["minor", "moderate", "major"], default="major",
                   help="Seuil de sévérité déclenchant l'échec (défaut: major)")
    p.add_argument("--ci-max-top-reg-pct", dest="ci_max_top_reg_pct", type=float, default=None,
                   help="Échec si la pire régression dépasse ce pourcentage (ex: 10.0)")
    # Output control (local only)
    p.add_argument("--aggregate-only", action="store_true", help="Affiche seulement la vue agrégée par kernel (pas de top par entrée)")
    p.add_argument("--aggregate-top", action="store_true", help="Affiche un top agrégé par kernel en tête du résumé")
    p.add_argument("--no-color", action="store_true", help="Désactive les couleurs ANSI (ou utilise NO_COLOR=1)")
    p.add_argument("--top-imp", dest="top_imp", type=int, default=None,
                   help="Nombre de meilleurs gains à afficher dans Top entries (défaut: 6)")
    p.add_argument("--show-all", action="store_true",
                   help="Affiche absolument toutes les mesures (toutes les entrées), sans troncature")
    return p.parse_args()


def main():
    args = parse_args()

    thresholds = DEFAULT_THRESHOLDS.copy()
    if args.thresholds:
        try:
            thr_user = json.loads(args.thresholds)
            thresholds.update({k: float(v) for k, v in thr_user.items()})
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Invalid thresholds JSON: {e}", file=sys.stderr)
            sys.exit(2)

    # Détermine si l'on active les couleurs ANSI
    color_enabled = should_enable_color(no_color_flag=args.no_color, stream=sys.stdout)

    ref_json = load_json(args.ref)
    cur_json = load_json(args.cur)

    ref_map = extract_benchmarks(ref_json)
    cur_map = extract_benchmarks(cur_json)

    # Filtre optionnel des benchmarks par nom (regex)
    if args.benchmark_filter:
        try:
            pattern = re.compile(args.benchmark_filter)
        except re.error as e:
            print(f"Invalid --benchmark-filter regex: {e}", file=sys.stderr)
            sys.exit(2)
        ref_map = {name: b for name, b in ref_map.items() if pattern.search(name)}
        cur_map = {name: b for name, b in cur_map.items() if pattern.search(name)}

    comparisons = compare_maps(ref_map, cur_map, args.metric, thresholds)

    # Affichage local: résumé rapide + vues agrégées
    regs = [c for c in comparisons if c.direction == "regression"]
    imps = [c for c in comparisons if c.direction == "improvement"]
    _print_section("Quick Summary", color_enabled=color_enabled)
    # Tableau vertical, une valeur par ligne
    total_val = ansi("1", str(len(comparisons)), enabled=color_enabled)
    regs_val = ansi("1;31", str(len(regs)), enabled=color_enabled) if len(regs) > 0 else ansi("1", "0", enabled=color_enabled)
    imps_val = ansi("1;32", str(len(imps)), enabled=color_enabled) if len(imps) > 0 else ansi("1", "0", enabled=color_enabled)
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
    # Pas de ligne vide supplémentaire ici; chaque section suivante imprime sa propre séparation
    aggs = aggregate_series(comparisons)
    if args.aggregate_top:
        _print_section("Aggregated per-kernel (top by mean rel change)", color_enabled=color_enabled)
        _print_aggregated_header()
        for a in aggs[:10]:
            mean_cell, min_cell, max_cell, dir_cell, sev_cell = _format_aggregated_cells(a, thresholds=thresholds, color_enabled=color_enabled)
            print(f"{a['kernel']:{KERNEL_COL_WIDTH}} | {a['count']:>3} | {mean_cell} | {min_cell} | {max_cell} | {dir_cell} | {sev_cell}")

    if args.aggregate_only:
        _print_section("Aggregated per-kernel view (mean/min/max relative change)", color_enabled=color_enabled)
        _print_aggregated_header()
        for a in aggs[:30]:
            mean_cell, min_cell, max_cell, dir_cell, sev_cell = _format_aggregated_cells(a, thresholds=thresholds, color_enabled=color_enabled)
            print(f"{a['kernel']:{KERNEL_COL_WIDTH}} | {a['count']:>3} | {mean_cell} | {min_cell} | {max_cell} | {dir_cell} | {sev_cell}")
    else:
        _print_section("Top entries", color_enabled=color_enabled)
        header = f"{'name':{NAME_COL_WIDTH}} | {'metric':{METRIC_COL_WIDTH}} | {'rel_chg':>8} | {'direction':>{DIR_COL_WIDTH}} | {'severity':>8}"
        print(header)
        print("-" * len(header))
        # Pires régressions
        regs_sorted = sorted(regs, key=_regression_magnitude_pct, reverse=True)
        reg_iter = regs_sorted if args.show_all else regs_sorted[:TOP_REG_COUNT]
        for c in reg_iter:
            rel_cell = pad_ansi(
                colorize_rel_change(c.relative_change, thresholds=thresholds, enabled=color_enabled),
                8,
                align='right'
            )
            # Sévérité d'affichage symétrique pour la colonne direction
            mag_pct_disp = abs(c.relative_change or 0.0) * 100.0
            sev_for_dir = classify_severity(mag_pct_disp, thresholds) if mag_pct_disp >= thresholds["minor_pct"] else "minor"
            dir_colored = colorize_direction(c.direction, sev_for_dir, enabled=color_enabled)
            dir_cell = pad_ansi(dir_colored, DIR_COL_WIDTH, align="right")
            name_cell = fit_text(c.name, NAME_COL_WIDTH)
            metric_cell = fit_text(c.metric, METRIC_COL_WIDTH)
            sev_cell = pad_ansi(
                colorize_severity_label(c.severity, c.direction, enabled=color_enabled),
                8,
                align='right',
            )
            print(f"{name_cell:{NAME_COL_WIDTH}} | {metric_cell:{METRIC_COL_WIDTH}} | {rel_cell} | {dir_cell} | {sev_cell}")

        # Séparateur horizontal
        print("-" * len(header))

        # Meilleurs gains
        # Prendre les N plus gros gains puis les afficher par ordre de changement croissant (plus négatif -> plus à gauche)
        n_imp = args.top_imp if args.top_imp is not None else TOP_IMP_COUNT
        imp_base = sorted(imps, key=_improvement_magnitude_pct, reverse=True)
        imp_selected = imp_base if args.show_all else imp_base[:n_imp]
        imp_selected = sorted(imp_selected, key=lambda c: (c.relative_change if c.relative_change is not None else 0.0))
        for c in imp_selected:
            rel_cell = pad_ansi(
                colorize_rel_change(c.relative_change, thresholds=thresholds, enabled=color_enabled),
                8,
                align='right'
            )
            mag_pct_disp = abs(c.relative_change or 0.0) * 100.0
            sev_for_dir = classify_severity(mag_pct_disp, thresholds) if mag_pct_disp >= thresholds["minor_pct"] else "minor"
            dir_colored = colorize_direction(c.direction, sev_for_dir, enabled=color_enabled)
            dir_cell = pad_ansi(dir_colored, DIR_COL_WIDTH, align="right")
            name_cell = fit_text(c.name, NAME_COL_WIDTH)
            metric_cell = fit_text(c.metric, METRIC_COL_WIDTH)
            sev_cell = pad_ansi(
                colorize_severity_label(c.severity, c.direction, enabled=color_enabled),
                8,
                align='right',
            )
            print(f"{name_cell:{NAME_COL_WIDTH}} | {metric_cell:{METRIC_COL_WIDTH}} | {rel_cell} | {dir_cell} | {sev_cell}")

        _print_section("Aggregated per-kernel view (mean/min/max relative change)", color_enabled=color_enabled)
        _print_aggregated_header()
        for a in aggs[:15]:
            kernel_cell = fit_text(a['kernel'], KERNEL_COL_WIDTH)
            mean_cell, min_cell, max_cell, dir_cell, sev_cell = _format_aggregated_cells(a, thresholds=thresholds, color_enabled=color_enabled)
            print(f"{kernel_cell:{KERNEL_COL_WIDTH}} | {a['count']:>3} | {mean_cell} | {min_cell} | {max_cell} | {dir_cell} | {sev_cell}")

    # Mode CI: appliquer les règles de gating et retourner un code d'erreur si nécessaire
    if args.ci:
        gate = evaluate_ci_gate(
            comparisons,
            fail_on_severity=args.ci_fail_on,
            max_top_reg_pct=args.ci_max_top_reg_pct,
        )
        _print_section("CI Gate", color_enabled=color_enabled)
        print(json.dumps(gate, indent=2))
        if gate["failed"]:
            print("CI gating: échec des règles de régression.", file=sys.stderr)
            sys.exit(4)


if __name__ == "__main__":
    main()


