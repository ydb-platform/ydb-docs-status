#!/usr/bin/env python3
"""Landing page and history index for the GitHub Pages site in ``docs/``.

Usage::

    ./scripts/index.py [<generated_at>]

Without arguments, ``lib.today_iso()`` is used along with the current
list of dates from ``docs/history/``. Produces two files:

* ``docs/index.html`` — site landing page (the GH Pages entry point):
  title, latest-run date, link to the current summary, links to up to
  5 most recent historical snapshots, and a link to the full history.
* ``docs/history/index.html`` — reverse-chronological list of all
  snapshots (each one linking to ``<date>/summary.html``).

Style and approach mirror ``report.py``/``summary.py``: a single
self-contained HTML file, inline CSS, no external resources.
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import lib  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Snapshot list
# ---------------------------------------------------------------------------

def history_dates() -> list[str]:
    """Subdirectory names of ``docs/history/`` in reverse chronological order.

    Folders are named ``YYYY-MM-DD``, so lexicographic sort matches
    chronological sort.
    """
    if not lib.HISTORY_ROOT.exists():
        return []
    dates = [p.name for p in lib.HISTORY_ROOT.iterdir() if p.is_dir()]
    return sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------

def render_landing(generated_at: str | None = None, dates: list[str] | None = None) -> Path:
    """Render ``docs/index.html``. Returns the path."""
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
            f" <a class=\"more\" href=\"history/index.html\">all snapshots ({len(dates)}) →</a>"
            if rest
            else " <a class=\"more\" href=\"history/index.html\">full list →</a>"
        )
        history_block = (
            "<section class=\"card\">\n"
            "  <h2>History</h2>\n"
            f"  <ul class=\"recent\">{items}</ul>\n"
            f"  <p class=\"more-line\">{more}</p>\n"
            "</section>\n"
        )
    else:
        history_block = (
            "<section class=\"card\">\n"
            "  <h2>History</h2>\n"
            "  <p class=\"muted\">No archived snapshots yet. They appear after "
            "the next <code>./analyze.py</code> run.</p>\n"
            "</section>\n"
        )

    body = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>YDB Documentation Status</title>\n"
        f"{lib.portal_head_links()}"
        f"<style>{_css()}</style>\n"
        "</head>\n<body>\n"
        "<main class=\"subsite-page\">\n"
        f"{lib.portal_crumbs()}"
        "<header class=\"page-header\">\n"
        "  <h1>YDB Documentation Status</h1>\n"
        "  <p class=\"src\">Compares the Russian and English documentation in "
        "<code>ydb-platform/ydb</code> across product versions.</p>\n"
        f"  <p class=\"src\">Last run: <code>{html.escape(when)}</code></p>\n"
        "</header>\n"
        "<section class=\"card primary\">\n"
        "  <h2>Latest report</h2>\n"
        "  <p><a class=\"big-link\" href=\"summary.html\">Cross-version summary →</a></p>\n"
        "  <p class=\"muted\">Version names in the summary are clickable — "
        "they lead to per-page score tables.</p>\n"
        "</section>\n"
        f"{history_block}"
        "</main>\n"
        "</body>\n</html>\n"
    )

    path = lib.SITE_ROOT / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    print(f"[index] wrote {path}")
    return path


# ---------------------------------------------------------------------------
# Full snapshot list
# ---------------------------------------------------------------------------

def render_history_index(dates: list[str] | None = None) -> Path:
    """Render ``docs/history/index.html``. Returns the path."""
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
            "<p class=\"muted\">Archive is empty — snapshots appear after "
            "<code>./analyze.py</code> runs.</p>"
        )

    body = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>YDB Documentation Status — history</title>\n"
        f"{lib.portal_head_links()}"
        f"<style>{_css()}</style>\n"
        "</head>\n<body>\n"
        "<main class=\"subsite-page\">\n"
        f"{lib.portal_crumbs('History')}"
        "<header class=\"page-header\">\n"
        "  <h1>Snapshot history</h1>\n"
        "  <p class=\"src\">Report states saved by date. "
        "Each snapshot opens as a self-contained summary.</p>\n"
        "</header>\n"
        f"<section class=\"card\">\n  {list_block}\n</section>\n"
        "</main>\n"
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
    """Page-specific CSS that sits on top of the portal stylesheet.

    Anything covered by ``portal.css`` (body, typography, ``code``, link
    colour, ``.portal-crumbs``) is intentionally not redefined here.
    """
    return (
        ".subsite-page{max-width:760px;margin:0 auto;padding:32px 24px 56px;}"
        "h1{margin:0 0 8px 0;font-size:26px;}"
        "h2{margin:0 0 12px 0;font-size:16px;color:#444;}"
        ".page-header{margin-bottom:24px;}"
        ".page-header .src{margin:4px 0;color:#555;font-size:13px;}"
        ".card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;"
        "padding:16px 20px;margin-bottom:20px;}"
        ".card.primary{border-color:#2399ff;}"
        ".big-link{font-size:18px;font-weight:600;text-decoration:none;}"
        ".big-link:hover{text-decoration:underline;}"
        ".muted{color:#888;font-size:13px;margin:6px 0 0 0;}"
        "ul.recent,ul.history{margin:0;padding-left:20px;font-size:14px;}"
        "ul.recent li,ul.history li{padding:3px 0;}"
        "ul.recent a,ul.history a{text-decoration:none;}"
        "ul.recent a:hover,ul.history a:hover{text-decoration:underline;}"
        ".more-line{margin:10px 0 0 0;font-size:13px;}"
        ".more-line .more{text-decoration:none;}"
        ".more-line .more:hover{text-decoration:underline;}"
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
        help="run date YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args(argv)
    dates = history_dates()
    render_landing(args.generated_at, dates)
    render_history_index(dates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
