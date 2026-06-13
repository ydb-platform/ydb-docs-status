#!/usr/bin/env python3
"""Archive previous site snapshots into ``docs/history/<old_date>/``.

Usage::

    ./scripts/archive.py [<today>]

``today`` is today's date in ``YYYY-MM-DD``; defaults to
``lib.today_iso()``. If ``docs/meta.json`` records a different date,
the current site snapshot (everything under ``docs/`` except the
``history/`` folder and the ``index.html`` landing page) is copied
into ``docs/history/<old_date>/``.

Idempotency:

* No ``docs/meta.json`` → nothing to archive, exit.
* ``old_date == today`` → re-run on the same day, no-op (the current
  files will simply be overwritten).
* ``docs/history/<old_date>/`` already exists → replaced wholesale by
  the current snapshot (last run of the day wins).
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import lib  # type: ignore[import-not-found]


#: Entries under ``docs/`` that are NOT part of a historical snapshot.
#: ``history`` is the archive itself. ``index.html`` is the site landing
#: page and is not needed inside each snapshot (history has its own
#: navigation).
_SNAPSHOT_EXCLUDE = {"history", "index.html"}


def archive_previous(today: str | None = None) -> str | None:
    """Copy the current ``docs/`` snapshot into ``docs/history/<old_date>/``.

    Returns the old snapshot date (``YYYY-MM-DD``) or ``None`` if there
    is nothing to archive (no ``meta.json``) or ``old_date == today``.
    """
    today = today or lib.today_iso()
    meta_path = lib.SITE_ROOT / "meta.json"
    if not meta_path.is_file():
        return None

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    old_date = meta.get("generated_at")
    if not old_date or old_date == today:
        return None

    target = lib.history_dir(old_date)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    for item in lib.SITE_ROOT.iterdir():
        if item.name in _SNAPSHOT_EXCLUDE:
            continue
        dst = target / item.name
        if item.is_dir():
            shutil.copytree(item, dst)
        else:
            shutil.copy2(item, dst)

    print(f"[archive] snapshot of {old_date} saved to {target}")
    return old_date


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "today",
        nargs="?",
        help="today's date YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args(argv)
    archive_previous(args.today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
