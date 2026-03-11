#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def add_core_to_path() -> None:
    override = os.getenv("APPLE_LOCAL_AI_CORE")
    if override:
        resolved_override = Path(override).resolve()
        if (resolved_override / "ailocaltools").exists():
            sys.path.insert(0, str(resolved_override))
            return
        raise RuntimeError(f"APPLE_LOCAL_AI_CORE does not contain ailocaltools: {resolved_override}")

    candidates: list[Path] = []

    current = Path(__file__).resolve()
    bundled_python = current.parent / "python"
    if (bundled_python / "ailocaltools").exists():
        sys.path.insert(0, str(bundled_python))
        return

    for parent in current.parents:
        candidates.append(parent / "python")
        candidates.append(parent / "core" / "src")

    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if (resolved / "ailocaltools").exists():
            sys.path.insert(0, key)
            return

    raise RuntimeError("Unable to locate core/src for ailocaltools.")


def main() -> int:
    add_core_to_path()
    from ailocaltools.bridge import cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
