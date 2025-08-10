#!/usr/bin/env python3
"""
BenchDiff entry point.

Loads package from `src/benchdiff` and delegates to the CLI runner.
"""

import os
import sys
import importlib.util


def _ensure_src_on_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(here, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


def _import_benchdiff_run():
    """Import benchdiff.run from src/benchdiff without static import (lint-friendly)."""
    here = os.path.dirname(os.path.abspath(__file__))
    init_path = os.path.join(here, "src", "benchdiff", "__init__.py")
    spec = importlib.util.spec_from_file_location("benchdiff", init_path)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load benchdiff from src/benchdiff/__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return getattr(module, "run")


def main() -> int:
    _ensure_src_on_path()
    run = _import_benchdiff_run()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())


