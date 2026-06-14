#!/usr/bin/env python3
"""Render ``docs/<version>/report.{txt,html}`` from ``results.json``.

Usage::

    ./scripts/report.py <version>

Two artefacts are produced side by side:

* ``report.txt`` — plain-text two-column table (score + RU URL). Useful
  for grep / diffs / scripting.
* ``report.html`` — single self-contained HTML with colour-coded score
  badges and clickable RU + EN links. Open it in a browser.

Both reports split pages into the main table and a separate
"expected single-language pages" section (rules from
``single_language_patterns`` in config.json).
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

import lib  # type: ignore[import-not-found]


def render(version: str, *, generated_at: str | None = None) -> tuple[Path, Path]:
    """Render text + HTML reports for ``version``.

    ``generated_at`` (``YYYY-MM-DD``) is stamped in the header of both files.
    Defaults to ``lib.today_iso()``.

    Returns ``(txt_path, html_path)``.
    """
    config = lib.load_config()
    entry = lib.require_version(version, config)
    url_version = entry.get("url_version")
    url_base = config.get("url_base", "https://ydb.tech/docs")
    when = generated_at or lib.today_iso()

    results_path = lib.site_version_dir(version) / "results.json"
    if not results_path.is_file():
        raise SystemExit(
            f"[report] {version}: {results_path} not found. Run ./scripts/compare.py {version} first."
        )
    results = json.loads(results_path.read_text(encoding="utf-8"))

    main_rows, single_rows = _build_rows(results, url_version, url_base)
    main_rows.sort(key=lambda r: (r["score"], r["rel"]))
    single_rows.sort(key=lambda r: r["rel"])

    hist = Counter(r["score"] for r in main_rows)
    by_section: dict[str, list[int]] = defaultdict(list)
    for r in main_rows:
        by_section[r["section"]].append(r["score"])

    txt_path = lib.site_version_dir(version) / "report.txt"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(
        _render_text(version, entry, when, main_rows, single_rows, hist, by_section),
        encoding="utf-8",
    )

    html_path = lib.site_version_dir(version) / "report.html"
    html_path.write_text(
        _render_html(version, entry, when, main_rows, single_rows, hist, by_section, config),
        encoding="utf-8",
    )

    print(
        f"[report] {version}: wrote {txt_path.name} + {html_path.name} "
        f"(main={len(main_rows)}, single-lang={len(single_rows)})"
    )
    return txt_path, html_path


# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------

def _build_rows(results: list[dict], url_version: str | None, url_base: str) -> tuple[list[dict], list[dict]]:
    main_rows: list[dict] = []
    single_rows: list[dict] = []
    for r in results:
        rel = r["rel"]
        ru_ok = r["ru_exists"]
        en_ok = r["en_exists"]
        single_expected = r.get("single_language_expected", False)
        ru_url = lib.page_to_url("ru", rel, url_version, url_base=url_base)
        en_url = lib.page_to_url("en", rel, url_version, url_base=url_base)
        section = Path(rel).parts[0] if Path(rel).parts else "(root)"

        if single_expected and not (ru_ok and en_ok):
            single_rows.append({
                "rel": rel,
                "ru_exists": ru_ok,
                "en_exists": en_ok,
                "ru_url": ru_url,
                "en_url": en_url,
                "section": section,
            })
            continue

        main_rows.append({
            "rel": rel,
            "ru_exists": ru_ok,
            "en_exists": en_ok,
            "ru_url": ru_url,
            "en_url": en_url,
            "section": section,
            "score": lib.int_score(r),
        })
    return main_rows, single_rows


# moved to lib.int_score


# ---------------------------------------------------------------------------
# Text rendering (kept for grep / diff workflows)
# ---------------------------------------------------------------------------

def _render_text(
    version: str,
    entry: dict,
    generated_at: str,
    main_rows: list[dict],
    single_rows: list[dict],
    hist: Counter,
    by_section: dict[str, list[int]],
) -> str:
    lines: list[str] = []
    lines.append(f"YDB ru/en docs comparison, version {version}")
    lines.append(f"Source: ydb-platform/ydb @ {entry['ref']}")
    lines.append(f"Generated: {generated_at}")
    lines.append("Scale: 1 — page missing or content significantly differs; 10 — content is very close.")
    lines.append(
        "Score is based on structural similarity (headings, length, code blocks, links, images)"
    )
    lines.append(
        "after include directives are expanded. This is a proxy for semantic match: with identical"
    )
    lines.append(
        "structure, wording can still differ. See documentation/scoring.md for details."
    )
    lines.append("")
    lines.append(f"{'Score':>6}  URL")
    lines.append(f"{'-----':>6}  ---")
    for r in main_rows:
        note = _text_note(r)
        line = f"{r['score']:>6}  {r['ru_url']}"
        if note:
            line += "  " + note
        lines.append(line)

    lines.append("")
    lines.append(f"Score distribution (pages: {len(main_rows)}):")
    for s in sorted(hist):
        lines.append(f"  {s:>2}: {hist[s]} pages")

    lines.append("")
    lines.append("By section (average score / page count):")
    for section in sorted(by_section):
        scores = by_section[section]
        avg = sum(scores) / len(scores)
        lines.append(f"  {section:<28} avg={avg:5.2f}  n={len(scores)}")

    if single_rows:
        lines.append("")
        lines.append(
            f"Expected single-language pages (per single_language_patterns, "
            f"total: {len(single_rows)})"
        )
        lines.append("Excluded from the main table. Edit the pattern list in config.json.")
        for r in single_rows:
            lang = "RU" if r["ru_exists"] else "EN"
            url = r["ru_url"] if r["ru_exists"] else r["en_url"]
            lines.append(f"  [{lang}-only]  {url}")

    return "\n".join(lines) + "\n"


def _text_note(r: dict) -> str:
    if not r["ru_exists"]:
        return "[no RU page]"
    if not r["en_exists"]:
        return "[no EN page]"
    return ""


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _render_html(
    version: str,
    entry: dict,
    generated_at: str,
    main_rows: list[dict],
    single_rows: list[dict],
    hist: Counter,
    by_section: dict[str, list[int]],
    config: dict,
) -> str:
    css = _build_css()
    head = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>YDB Documentation Status — {html.escape(version)}</title>\n"
        f"{lib.portal_head_links()}"
        f"<style>{css}</style>\n"
        "</head>\n<body>\n"
        "<main class=\"subsite-page\">\n"
        f"{lib.portal_crumbs(f'Version {version}')}"
    )

    header = (
        "<header class=\"page-header\">\n"
        f"  <h1>Version <span class=\"ver\">{html.escape(version)}</span></h1>\n"
        f"  <p class=\"src\">Source: <code>ydb-platform/ydb @ {html.escape(entry['ref'])}</code></p>\n"
        f"  <p class=\"src\">Generated: <code>{html.escape(generated_at)}</code></p>\n"
        "  <p class=\"legend\">Scale: <span class=\"badge score-1\">1</span> — page missing or significantly different; "
        "<span class=\"badge score-10\">10</span> — versions are nearly identical. "
        "Methodology details: <code>documentation/scoring.md</code>.</p>\n"
        "</header>\n"
    )

    stats = _render_stats_block(main_rows, hist, by_section)
    main_table = _render_main_table(main_rows)
    single_block = _render_single_block(single_rows, config)

    return head + header + stats + main_table + single_block + "</main>\n</body>\n</html>\n"


def _render_stats_block(main_rows: list[dict], hist: Counter, by_section: dict[str, list[int]]) -> str:
    total = len(main_rows)

    hist_rows = []
    for s in sorted(hist):
        bg, fg = lib.SCORE_COLORS[s]
        pct = 100 * hist[s] / total if total else 0
        hist_rows.append(
            f"<tr><td><span class=\"badge\" style=\"background:{bg};color:{fg};\">{s}</span></td>"
            f"<td class=\"num\">{hist[s]}</td>"
            f"<td class=\"num muted\">{pct:.1f}%</td></tr>"
        )
    hist_html = (
        "<div class=\"card\">\n"
        f"  <h2>Score distribution <span class=\"muted\">({total})</span></h2>\n"
        "  <table class=\"compact\">\n"
        "    <thead><tr><th>Score</th><th class=\"num\">Pages</th><th class=\"num\">Share</th></tr></thead>\n"
        f"    <tbody>{''.join(hist_rows)}</tbody>\n"
        "  </table>\n"
        "</div>\n"
    )

    section_rows = []
    for section in sorted(by_section):
        scores = by_section[section]
        avg = sum(scores) / len(scores)
        avg_rounded = max(1, min(10, round(avg)))
        bg, fg = lib.SCORE_COLORS[avg_rounded]
        section_rows.append(
            f"<tr><td>{html.escape(section)}</td>"
            f"<td><span class=\"badge\" style=\"background:{bg};color:{fg};\">{avg:.2f}</span></td>"
            f"<td class=\"num\">{len(scores)}</td></tr>"
        )
    sections_html = (
        "<div class=\"card\">\n"
        f"  <h2>By section <span class=\"muted\">({len(by_section)})</span></h2>\n"
        "  <table class=\"compact\">\n"
        "    <thead><tr><th>Section</th><th>Average</th><th class=\"num\">Pages</th></tr></thead>\n"
        f"    <tbody>{''.join(section_rows)}</tbody>\n"
        "  </table>\n"
        "</div>\n"
    )

    return "<section class=\"stats\">\n" + hist_html + sections_html + "</section>\n"


def _render_main_table(main_rows: list[dict]) -> str:
    body = []
    for r in main_rows:
        bg, fg = lib.SCORE_COLORS[r["score"]]
        ru_cell = (
            f"<a href=\"{html.escape(r['ru_url'])}\" target=\"_blank\" rel=\"noopener\">RU</a>"
            if r["ru_exists"] else
            "<span class=\"missing\">—</span>"
        )
        en_cell = (
            f"<a href=\"{html.escape(r['en_url'])}\" target=\"_blank\" rel=\"noopener\">EN</a>"
            if r["en_exists"] else
            "<span class=\"missing\">—</span>"
        )
        rel = html.escape(r["rel"])
        body.append(
            "<tr>"
            f"<td class=\"score-cell\"><span class=\"badge\" style=\"background:{bg};color:{fg};\">{r['score']}</span></td>"
            f"<td class=\"rel\">{rel}</td>"
            f"<td class=\"lang\">{ru_cell}</td>"
            f"<td class=\"lang\">{en_cell}</td>"
            "</tr>"
        )
    return (
        "<section class=\"main\">\n"
        f"  <h2>Pages <span class=\"muted\">({len(main_rows)})</span></h2>\n"
        "  <table class=\"pages\">\n"
        "    <thead><tr>"
        "<th>Score</th><th>Page</th><th>RU</th><th>EN</th>"
        "</tr></thead>\n"
        f"    <tbody>{''.join(body)}</tbody>\n"
        "  </table>\n"
        "</section>\n"
    )


def _render_single_block(single_rows: list[dict], config: dict) -> str:
    if not single_rows:
        return ""
    patterns = config.get("single_language_patterns", [])
    pattern_chips = " ".join(f"<code>{html.escape(p)}</code>" for p in patterns) or "—"
    items = []
    for r in single_rows:
        if r["ru_exists"]:
            tag = "<span class=\"tag tag-ru\">RU-only</span>"
            url = r["ru_url"]
        else:
            tag = "<span class=\"tag tag-en\">EN-only</span>"
            url = r["en_url"]
        items.append(
            "<li>"
            f"{tag} <a href=\"{html.escape(url)}\" target=\"_blank\" rel=\"noopener\">{html.escape(r['rel'])}</a>"
            "</li>"
        )
    return (
        "<section class=\"single\">\n"
        f"  <h2>Expected single-language pages <span class=\"muted\">({len(single_rows)})</span></h2>\n"
        f"  <p class=\"hint\">Excluded from the main table. Patterns: {pattern_chips}. "
        "Edit in <code>config.json → single_language_patterns</code>.</p>\n"
        f"  <ul class=\"single-list\">{''.join(items)}</ul>\n"
        "</section>\n"
    )


def _build_css() -> str:
    """Page-specific CSS layered on top of the portal stylesheet."""
    return (
        ".subsite-page{max-width:1200px;margin:0 auto;padding:32px 24px 56px;}"
        "h1{margin:0 0 8px 0;font-size:22px;}"
        "h2{margin:0 0 12px 0;font-size:16px;color:#444;}"
        ".page-header{margin-bottom:24px;}"
        ".page-header .ver{color:#1a9850;}"
        ".page-header .src{margin:4px 0;color:#555;font-size:13px;}"
        ".page-header .legend{margin:8px 0 0 0;color:#555;font-size:13px;}"
        ".muted{color:#888;font-weight:400;font-size:0.9em;}"
        ".stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));"
        "gap:16px;margin-bottom:24px;}"
        ".card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;}"
        ".card table.compact{width:100%;border-collapse:collapse;font-size:13px;}"
        ".card table.compact th{text-align:left;color:#666;font-weight:500;"
        "padding:4px 8px;border-bottom:1px solid #e5e7eb;}"
        ".card table.compact td{padding:4px 8px;border-bottom:1px solid #f0f0f0;}"
        ".card table.compact tr:last-child td{border-bottom:none;}"
        ".num{text-align:right;font-variant-numeric:tabular-nums;}"
        ".badge{display:inline-block;min-width:24px;padding:2px 8px;border-radius:4px;"
        "font-weight:600;font-size:12px;text-align:center;}"
        "section.main,section.single{background:#fff;border:1px solid #e5e7eb;"
        "border-radius:8px;padding:16px;margin-bottom:24px;}"
        "table.pages{width:100%;border-collapse:collapse;font-size:13px;}"
        "table.pages th{text-align:left;color:#666;font-weight:500;padding:8px 12px;"
        "border-bottom:1px solid #e5e7eb;position:sticky;top:0;background:#fff;}"
        "table.pages td{padding:6px 12px;border-bottom:1px solid #f4f5f7;}"
        "table.pages tr:hover td{background:#f9fafb;}"
        "table.pages .score-cell{width:60px;}"
        "table.pages .rel{font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,monospace;"
        "color:#333;}"
        "table.pages .lang{width:48px;text-align:center;}"
        "table.pages .lang a{text-decoration:none;font-weight:600;}"
        "table.pages .lang a:hover{text-decoration:underline;}"
        "table.pages .missing{color:#999;}"
        ".tag{display:inline-block;padding:1px 8px;border-radius:10px;"
        "font-size:11px;font-weight:600;margin-right:6px;}"
        ".tag-ru{background:#fde7e9;color:#a33;}"
        ".tag-en{background:#e7eafd;color:#33a;}"
        "section.single .hint{color:#555;font-size:13px;margin:0 0 12px 0;}"
        "section.single ul.single-list{margin:0;padding:0;list-style:none;"
        "font-size:13px;}"
        "section.single ul.single-list li{padding:4px 0;border-bottom:1px solid #f4f5f7;}"
        "section.single ul.single-list li:last-child{border-bottom:none;}"
        "section.single ul.single-list a{text-decoration:none;"
        "font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,monospace;}"
        "section.single ul.single-list a:hover{text-decoration:underline;}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="version key from config.json (e.g. 25.3)")
    args = parser.parse_args(argv)
    render(args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
