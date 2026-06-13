#!/usr/bin/env python3
"""Compare the ru/en YDB docs and build reports.

Usage::

    ./analyze.py                  # all versions from the config
    ./analyze.py 25.3 main        # subset

Steps:

1. ``archive`` — if ``docs/meta.json`` records a previous date, copy
   the current site snapshot into ``docs/history/<old_date>/``.
2. ``compare`` / ``report`` — for each requested version: pairwise
   metrics (``docs/<v>/results.json``) and the user-facing report
   (``docs/<v>/report.{txt,html}``).
3. ``summary`` — cross-version overview ``docs/summary.{txt,html}``
   (every version with a ``results.json`` on disk).
4. ``index`` — refresh the landing page ``docs/index.html`` and
   ``docs/history/index.html``.
5. Write ``docs/meta.json`` with the run date.

Source docs must be fetched first via ``./download.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import lib  # type: ignore[import-not-found]  # noqa: E402
import archive as archive_mod  # type: ignore[import-not-found]  # noqa: E402
import compare as compare_mod  # type: ignore[import-not-found]  # noqa: E402
import index as index_mod  # type: ignore[import-not-found]  # noqa: E402
import report as report_mod  # type: ignore[import-not-found]  # noqa: E402
import summary as summary_mod  # type: ignore[import-not-found]  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("versions", nargs="*", help="versions (default: all from config.json)")
    args = parser.parse_args(argv)

    config = lib.load_config()
    targets = args.versions or list(config["versions"].keys())
    for v in targets:
        lib.require_version(v, config)

    today = lib.today_iso()

    print("\n=== archive ===")
    archive_mod.archive_previous(today)

    for v in targets:
        print(f"\n=== {v} ===")
        compare_mod.compare(v)
        report_mod.render(v, generated_at=today)

    print("\n=== summary ===")
    summary_mod.render(generated_at=today)

    print("\n=== index ===")
    dates = index_mod.history_dates()
    index_mod.render_landing(today, dates)
    index_mod.render_history_index(dates)

    meta_path = lib.SITE_ROOT / "meta.json"
    meta_path.write_text(
        json.dumps({"generated_at": today}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[meta] wrote {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
