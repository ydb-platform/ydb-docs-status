#!/usr/bin/env python3
"""Архив прошлых снимков сайта в ``docs/history/<old_date>/``.

Использование::

    ./scripts/archive.py [<today>]

``today`` — дата сегодняшнего прогона в формате ``YYYY-MM-DD``;
если не задана, берётся ``lib.today_iso()``. Если в ``docs/meta.json``
есть запись с другой датой, текущий снимок сайта (всё содержимое
``docs/``, кроме самой папки ``history/`` и лендинга ``index.html``)
копируется в ``docs/history/<old_date>/``.

Идемпотентность:

* Если ``docs/meta.json`` нет — нечего архивировать, выход.
* Если ``old_date == today`` — повторный прогон в тот же день,
  ничего не делаем (текущая запись перезапишется аналогично).
* Если ``docs/history/<old_date>/`` уже существует — она целиком
  заменяется текущим снимком (последний прогон того дня выигрывает).
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import lib  # type: ignore[import-not-found]


#: Файлы/каталоги в ``docs/``, которые не входят в исторический снимок.
#: ``history`` — сам архив. ``index.html`` — лендинг сайта, в каждом
#: снимке не нужен (внутри истории своя навигация).
_SNAPSHOT_EXCLUDE = {"history", "index.html"}


def archive_previous(today: str | None = None) -> str | None:
    """Скопировать текущий снимок ``docs/`` в ``docs/history/<old_date>/``.

    Возвращает дату старого снимка (``YYYY-MM-DD``) или ``None``, если
    архивировать нечего (нет ``meta.json``) либо ``old_date == today``.
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
        help="дата сегодняшнего прогона YYYY-MM-DD (по умолчанию — сегодня)",
    )
    args = parser.parse_args(argv)
    archive_previous(args.today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
