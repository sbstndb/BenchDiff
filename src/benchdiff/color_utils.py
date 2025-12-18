"""
color_utils.py

Centralized utilities for ANSI coloring and formatting of outputs
related to performance regressions/improvements.

Objectives:
- A single implementation for ANSI colors and padding
- Explicit configuration via thresholds provided by the caller
- Automatic activation/deactivation (TTY, NO_COLOR) or via flag
"""

from __future__ import annotations

import os
import re
import sys
from typing import Dict, Optional


# Regex to strip ANSI sequences
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Unified (symmetric) color palette by severity and direction
# - regression: minor=yellow (33), moderate=red (31), major=bright red (91)
# - improvement: minor=green (32), moderate=bright green (92), major=bold bright green (1;92)
SEVERITY_COLOR = {
    "regression": {"minor": "33", "moderate": "31", "major": "1;91"},
    "improvement": {"minor": "32", "moderate": "92", "major": "1;92"},
}
NEUTRAL_COLOR = "90"  # gray for NA / none / unchanged / unknown
NEUTRAL_CHANGE_COLOR = "36"  # cyan for ~neutral changes (below threshold)


def should_enable_color(no_color_flag: bool = False, stream = sys.stdout) -> bool:
    """Determines whether ANSI colors should be enabled (flag, NO_COLOR, TTY)."""
    if no_color_flag or os.environ.get("NO_COLOR") is not None:
        return False
    try:
        return bool(getattr(stream, "isatty", lambda: False)())
    except OSError:
        return False


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def ansi(color_code: str, text: str, *, enabled: bool = True) -> str:
    """Applies ANSI code if enabled=True, otherwise returns plain text."""
    return text if not enabled else f"\033[{color_code}m{text}\033[0m"


def pad_ansi(colored_text: str, width: int, *, align: str = "right") -> str:
    """Pads a potentially ANSI-colored string to a fixed width (align left/right)."""
    visible_len = len(strip_ansi(colored_text))
    pad = max(0, width - visible_len)
    return colored_text + (" " * pad) if align == "left" else (" " * pad) + colored_text


def classify_severity(magnitude_pct: float, thresholds: Dict[str, float]) -> str:
    """Classifies regression severity based on a positive percentage."""
    return (
        "major" if magnitude_pct >= thresholds["major_pct"]
        else "moderate" if magnitude_pct >= thresholds["moderate_pct"]
        else "minor"
    )


def _severity_color(direction: str, severity: str) -> str:
    mapping = SEVERITY_COLOR.get(direction, {})
    return mapping.get(severity, NEUTRAL_COLOR)


def colorize_direction(direction: str, severity: str, *, enabled: bool = True) -> str:
    """Colorizes the direction label: regression/improvement/unchanged/unknown."""
    if direction in {"regression", "improvement"}:
        sev = severity if (direction == "regression" or severity in {"minor", "moderate", "major"}) else "minor"
        return ansi(_severity_color(direction, sev), direction, enabled=enabled)
    return ansi(NEUTRAL_COLOR, direction, enabled=enabled)


def colorize_severity_label(severity: str, direction: str, *, enabled: bool = True) -> str:
    """Colorizes the severity label according to the direction."""
    return (
        ansi(NEUTRAL_COLOR, severity, enabled=enabled)
        if severity not in {"minor", "moderate", "major"}
        else ansi(_severity_color(direction, severity), severity, enabled=enabled)
    )


def colorize_rel_change(value: Optional[float], *, thresholds: Dict[str, float], enabled: bool = True) -> str:
    """Colorizes a relative change (e.g., +0.123 -> +12.3%) with symmetric palette.

    Convention (time-like metrics):
    - value > 0: regression (red/yellow code based on severity)
    - value < 0: improvement (green code based on severity)
    - |value| < minor_pct: neutral color (cyan)
    - value == 0: neutral color (cyan)
    """
    if value is None:
        return "NA"
    mag_pct = abs(value) * 100.0
    if mag_pct < thresholds["minor_pct"]:
        return ansi(NEUTRAL_CHANGE_COLOR, f"{value*100:+.2f}%", enabled=enabled)
    sev = classify_severity(mag_pct, thresholds)
    if value > 0:
        code = _severity_color("regression", sev)
    elif value < 0:
        code = _severity_color("improvement", sev)
    else:
        code = NEUTRAL_CHANGE_COLOR
    return ansi(code, f"{value*100:+.2f}%", enabled=enabled)


def fit_text(text: Optional[str], width: int) -> str:
    """Truncates/extends text to fixed width (without color)."""
    if text is None:
        return "".ljust(width)
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."
