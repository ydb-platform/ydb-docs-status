#!/usr/bin/env python3
"""Скачать документацию YDB для всех версий из ``config.json`` в ``cache/``.

Использование::

    ./download.py                  # все версии из конфига
    ./download.py 25.3 25.4        # только указанные версии
    ./download.py --refresh main   # принудительно перекачать

Каждая версия идёт через sparse-checkout (только ``ydb/docs/``), так что
на диск ложится ~100 МБ на версию, а не полный клон. Без ``--refresh``
уже скачанные версии пропускаются. Папка ``cache/`` целиком в
``.gitignore`` — это исходники, не часть публикуемого сайта.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Подключаем scripts/ к sys.path, чтобы импортировать утилиты.
_SCRIPTS = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import lib  # type: ignore[import-not-found]  # noqa: E402
import fetch as fetch_mod  # type: ignore[import-not-found]  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("versions", nargs="*", help="версии (по умолчанию: все из config.json)")
    parser.add_argument("--refresh", action="store_true", help="перекачать, даже если папка уже есть")
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
