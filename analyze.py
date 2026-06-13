#!/usr/bin/env python3
"""Сравнить ru/en версии документации YDB и собрать отчёты.

Использование::

    ./analyze.py                  # все версии из конфига
    ./analyze.py 25.3 main        # только указанные

Шаги:

1. ``archive``  — если в ``docs/meta.json`` уже стоит прошлая дата,
   копируем текущий снимок сайта в ``docs/history/<old_date>/``.
2. ``compare`` / ``report`` — для каждой запрошенной версии: попарные
   метрики (``docs/<v>/results.json``) и пользовательский отчёт
   (``docs/<v>/report.{txt,html}``).
3. ``summary`` — кросс-версионная сводка ``docs/summary.{txt,html}``
   (по всем версиям, у которых на диске есть ``results.json``).
4. ``index`` — обновляем лендинг ``docs/index.html`` и
   ``docs/history/index.html``.
5. Пишем ``docs/meta.json`` с датой прогона.

Перед первым прогоном нужны исходники: ``./download.py``.
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
    parser.add_argument("versions", nargs="*", help="версии (по умолчанию: все из config.json)")
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
