#!/usr/bin/env python3
"""Лендинг и индекс истории для GH Pages сайта в ``docs/``.

Использование::

    ./scripts/index.py [<generated_at>]

Без аргументов — берётся ``lib.today_iso()`` и текущий список дат из
``docs/history/``. Производит два файла:

* ``docs/index.html`` — главная страница сайта (точка входа GH Pages):
  заголовок, дата последнего прогона, ссылка на свежую сводку, ссылки
  на 5 последних исторических снимков и на полный список истории.
* ``docs/history/index.html`` — обратный хронологический список всех
  снимков (``<date>/summary.html``).

Стиль и подход — те же, что в ``report.py``/``summary.py``: один
self-contained HTML, CSS встроен, никаких внешних ресурсов.
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import lib  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Сбор списка снимков
# ---------------------------------------------------------------------------

def history_dates() -> list[str]:
    """Имена подпапок ``docs/history/`` в обратном хронологическом порядке.

    Подпапки именуются ``YYYY-MM-DD``, поэтому лексикографическая
    сортировка совпадает с хронологической.
    """
    if not lib.HISTORY_ROOT.exists():
        return []
    dates = [p.name for p in lib.HISTORY_ROOT.iterdir() if p.is_dir()]
    return sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# Лендинг
# ---------------------------------------------------------------------------

def render_landing(generated_at: str | None = None, dates: list[str] | None = None) -> Path:
    """Сгенерировать ``docs/index.html``. Возвращает путь."""
    when = generated_at or lib.today_iso()
    if dates is None:
        dates = history_dates()

    recent = dates[:5]
    rest = max(0, len(dates) - len(recent))

    history_block: str
    if dates:
        items = "".join(
            f"<li><a href=\"history/{html.escape(d)}/summary.html\">{html.escape(d)}</a></li>"
            for d in recent
        )
        more = (
            f" <a class=\"more\" href=\"history/index.html\">все снимки ({len(dates)}) →</a>"
            if rest
            else " <a class=\"more\" href=\"history/index.html\">полный список →</a>"
        )
        history_block = (
            "<section class=\"card\">\n"
            "  <h2>История</h2>\n"
            f"  <ul class=\"recent\">{items}</ul>\n"
            f"  <p class=\"more-line\">{more}</p>\n"
            "</section>\n"
        )
    else:
        history_block = (
            "<section class=\"card\">\n"
            "  <h2>История</h2>\n"
            "  <p class=\"muted\">Пока нет архивных снимков. Они появятся "
            "после следующего прогона <code>./analyze.py</code>.</p>\n"
            "</section>\n"
        )

    body = (
        "<!DOCTYPE html>\n<html lang=\"ru\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<title>YDB docs sync</title>\n"
        f"<style>{_css()}</style>\n"
        "</head>\n<body>\n"
        "<header class=\"page-header\">\n"
        "  <h1>YDB docs sync</h1>\n"
        "  <p class=\"src\">Сравнение русской и английской документации "
        "<code>ydb-platform/ydb</code> по продуктовым версиям.</p>\n"
        f"  <p class=\"src\">Последний прогон: <code>{html.escape(when)}</code></p>\n"
        "</header>\n"
        "<section class=\"card primary\">\n"
        "  <h2>Актуальный отчёт</h2>\n"
        "  <p><a class=\"big-link\" href=\"summary.html\">Сводка по версиям →</a></p>\n"
        "  <p class=\"muted\">Из сводки кликабельны имена версий — там "
        "пер-страничные таблицы с оценками.</p>\n"
        "</section>\n"
        f"{history_block}"
        "</body>\n</html>\n"
    )

    path = lib.SITE_ROOT / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    print(f"[index] wrote {path}")
    return path


# ---------------------------------------------------------------------------
# Полный список снимков
# ---------------------------------------------------------------------------

def render_history_index(dates: list[str] | None = None) -> Path:
    """Сгенерировать ``docs/history/index.html``. Возвращает путь."""
    if dates is None:
        dates = history_dates()

    if dates:
        items = "".join(
            f"<li><a href=\"{html.escape(d)}/summary.html\">{html.escape(d)}</a></li>"
            for d in dates
        )
        list_block = f"<ul class=\"history\">{items}</ul>"
    else:
        list_block = (
            "<p class=\"muted\">Архив пуст — снимки появляются после прогонов "
            "<code>./analyze.py</code>.</p>"
        )

    body = (
        "<!DOCTYPE html>\n<html lang=\"ru\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<title>YDB docs sync — история</title>\n"
        f"<style>{_css()}</style>\n"
        "</head>\n<body>\n"
        "<header class=\"page-header\">\n"
        "  <p class=\"crumbs\"><a href=\"../index.html\">← на главную</a></p>\n"
        "  <h1>История снимков</h1>\n"
        "  <p class=\"src\">Сохранённые состояния отчётов по датам. "
        "Каждый снимок открывается как самостоятельная сводка.</p>\n"
        "</header>\n"
        f"<section class=\"card\">\n  {list_block}\n</section>\n"
        "</body>\n</html>\n"
    )

    path = lib.HISTORY_ROOT / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    print(f"[index] wrote {path}")
    return path


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _css() -> str:
    return (
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "color:#1d1d1f;background:#f6f7f9;margin:0;padding:24px 32px;line-height:1.45;"
        "max-width:760px;}"
        "h1{margin:0 0 8px 0;font-size:26px;}"
        "h2{margin:0 0 12px 0;font-size:16px;color:#444;}"
        ".page-header{margin-bottom:20px;}"
        ".page-header .src{margin:4px 0;color:#555;font-size:13px;}"
        ".page-header .crumbs{margin:0 0 8px 0;font-size:13px;}"
        ".page-header .crumbs a{color:#0969da;text-decoration:none;}"
        ".page-header .crumbs a:hover{text-decoration:underline;}"
        ".card{background:#fff;border:1px solid #e1e4e8;border-radius:8px;"
        "padding:16px 20px;margin-bottom:20px;}"
        ".card.primary{border-color:#a6d96a;}"
        ".big-link{font-size:18px;font-weight:600;color:#0969da;text-decoration:none;}"
        ".big-link:hover{text-decoration:underline;}"
        ".muted{color:#888;font-size:13px;margin:6px 0 0 0;}"
        "ul.recent,ul.history{margin:0;padding-left:20px;font-size:14px;}"
        "ul.recent li,ul.history li{padding:3px 0;}"
        "ul.recent a,ul.history a{color:#0969da;text-decoration:none;}"
        "ul.recent a:hover,ul.history a:hover{text-decoration:underline;}"
        ".more-line{margin:10px 0 0 0;font-size:13px;}"
        ".more-line .more{color:#0969da;text-decoration:none;}"
        ".more-line .more:hover{text-decoration:underline;}"
        "code{background:#f4f5f7;padding:1px 5px;border-radius:3px;font-size:12px;}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "generated_at",
        nargs="?",
        help="дата прогона YYYY-MM-DD (по умолчанию — сегодня)",
    )
    args = parser.parse_args(argv)
    dates = history_dates()
    render_landing(args.generated_at, dates)
    render_history_index(dates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
