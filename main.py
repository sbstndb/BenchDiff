#!/usr/bin/env python3
"""
BenchDiff entry point.

Delegates to the CLI runner defined in `cli.py` to keep this module minimal
and maintain backward-compatible invocation:

    python main.py --ref ref.json --cur cur.json [options]
"""

from cli import run


if __name__ == "__main__":
    raise SystemExit(run())


