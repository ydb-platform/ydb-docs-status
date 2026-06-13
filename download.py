#!/usr/bin/env python3
"""Fetch YDB documentation for every version in ``config.json`` into ``cache/``.

Usage::

    ./download.py                  # all versions from the config
    ./download.py 25.3 25.4        # subset
    ./download.py --refresh main   # force re-fetch

Each version is sparse-checked-out (only ``ydb/docs/``), so the disk
footprint is ~100 MB per version rather than a full clone. Without
``--refresh`` already-fetched versions are skipped. The ``cache/``
directory is fully gitignored — it holds input data, not part of the
published site.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Put scripts/ on sys.path so helper modules can be imported by short name.
_SCRIPTS = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import lib  # type: ignore[import-not-found]  # noqa: E402
import fetch as fetch_mod  # type: ignore[import-not-found]  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("versions", nargs="*", help="versions (default: all from config.json)")
    parser.add_argument("--refresh", action="store_true", help="re-fetch even if the folder already exists")
    args = parser.parse_args(argv)

    config = lib.load_config()
    targets = args.versions or list(config["versions"].keys())
    for v in targets:
        lib.require_version(v, config)

    for v in targets:
        print(f"\n=== {v} ===")
        fetch_mod.fetch(v, refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
