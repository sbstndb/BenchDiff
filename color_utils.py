"""
color_utils.py

Utilitaires centralisés pour la coloration ANSI et la mise en forme
des sorties liées aux régressions/améliorations de performances.

Objectifs:
- Une seule implémentation pour les couleurs et le padding ANSI
- Paramétrage explicite via thresholds fournis par l'appelant
- Activation/désactivation automatique (TTY, NO_COLOR) ou via flag
"""

from __future__ import annotations

import os
import re
import sys
from typing import Dict, Optional


# Regex pour supprimer les séquences ANSI
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Palette unifiée (symétrique) par sévérité et direction
# - regression: minor=jaune (33), moderate=rouge (31), major=rouge vif (91)
# - improvement: minor=vert (32), moderate=vert vif (92), major=vert vif gras (1;92)
SEVERITY_COLOR = {
    "regression": {"minor": "33", "moderate": "31", "major": "1;91"},
    "improvement": {"minor": "32", "moderate": "92", "major": "1;92"},
}
NEUTRAL_COLOR = "90"  # gris pour NA / none / unchanged / unknown
NEUTRAL_CHANGE_COLOR = "36"  # cyan pour changements ~neutres (sous seuil)


def should_enable_color(no_color_flag: bool = False, stream = sys.stdout) -> bool:
    """Détermine si les couleurs ANSI doivent être activées (flag, NO_COLOR, TTY)."""
    if no_color_flag or os.environ.get("NO_COLOR") is not None:
        return False
    try:
        return bool(getattr(stream, "isatty", lambda: False)())
    except OSError:
        return False


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def ansi(color_code: str, text: str, *, enabled: bool = True) -> str:
    """Applique le code ANSI si enabled=True, sinon retourne text brut."""
    return text if not enabled else f"\033[{color_code}m{text}\033[0m"


def pad_ansi(colored_text: str, width: int, *, align: str = "right") -> str:
    """Pad une chaîne potentiellement colorée ANSI à une largeur fixe (align left/right)."""
    visible_len = len(strip_ansi(colored_text))
    pad = max(0, width - visible_len)
    return colored_text + (" " * pad) if align == "left" else (" " * pad) + colored_text


def classify_severity(magnitude_pct: float, thresholds: Dict[str, float]) -> str:
    """Classe la sévérité d'une régression en fonction d'un pourcentage positif."""
    return (
        "major" if magnitude_pct >= thresholds["major_pct"]
        else "moderate" if magnitude_pct >= thresholds["moderate_pct"]
        else "minor"
    )


def _severity_color(direction: str, severity: str) -> str:
    mapping = SEVERITY_COLOR.get(direction, {})
    return mapping.get(severity, NEUTRAL_COLOR)


def colorize_direction(direction: str, severity: str, *, enabled: bool = True) -> str:
    """Colorise le libellé de direction: regression/improvement/unchanged/unknown."""
    if direction in {"regression", "improvement"}:
        sev = severity if (direction == "regression" or severity in {"minor", "moderate", "major"}) else "minor"
        return ansi(_severity_color(direction, sev), direction, enabled=enabled)
    return ansi(NEUTRAL_COLOR, direction, enabled=enabled)


def colorize_severity_label(severity: str, direction: str, *, enabled: bool = True) -> str:
    """Colorise l'étiquette de sévérité selon la direction."""
    return (
        ansi(NEUTRAL_COLOR, severity, enabled=enabled)
        if severity not in {"minor", "moderate", "major"}
        else ansi(_severity_color(direction, severity), severity, enabled=enabled)
    )


def colorize_rel_change(value: Optional[float], *, thresholds: Dict[str, float], enabled: bool = True) -> str:
    """Colorise un changement relatif (ex: +0.123 -> +12.3%) avec palette symétrique.

    Convention (temps-like):
    - value > 0: régression (code rouge/jaune selon sévérité)
    - value < 0: amélioration (code vert selon sévérité)
    - |value| < minor_pct: couleur neutre (cyan)
    - value == 0: couleur neutre (cyan)
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
    """Tronque/étend le texte à largeur fixe (sans couleur)."""
    if text is None:
        return "".ljust(width)
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


