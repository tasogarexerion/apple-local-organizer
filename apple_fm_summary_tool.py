#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "core" / "src"))
    from ailocaltools.cli import legacy_summary_main

    return legacy_summary_main()


if __name__ == "__main__":
    raise SystemExit(main())
