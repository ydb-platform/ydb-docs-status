#!/usr/bin/env python3
"""Cross-version summary report.

Usage::

    ./scripts/summary.py

Reads ``docs/<v>/results.json`` for every version listed in
``config.json`` and produces:

* ``docs/summary.txt`` — compact text overview (totals, score
  distribution matrix, per-section averages).
* ``docs/summary.html`` — interactive cross-version view with
  colour-coded cells and clickable per-version reports.

Versions whose ``results.json`` is missing are skipped with a warning;
re-run ``./analyze.py`` (or just ``compare.py``) to fill them in.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

import lib  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _per_version_stats(results: list[dict]) -> dict:
    """Reduce a ``results.json`` array to summary statistics.

    Pages marked ``single_language_expected`` that exist only on one side
    are excluded from the main figures and counted separately, mirroring
    what ``report.py`` does.
    """
    main_scores: list[int] = []
    by_section: dict[str, list[int]] = defaultdict(list)
    single = 0
    for r in results:
        ru = r["ru_exists"]
        en = r["en_exists"]
        if r.get("single_language_expected", False) and not (ru and en):
            single += 1
            continue
        s = lib.int_score(r)
        main_scores.append(s)
        section = Path(r["rel"]).parts[0] if Path(r["rel"]).parts else "(root)"
        by_section[section].append(s)
    avg = sum(main_scores) / len(main_scores) if main_scores else 0.0
    return {
        "total": len(main_scores),
        "single_lang": single,
        "avg": avg,
        "hist": Counter(main_scores),
        "by_section": {sec: (sum(v) / len(v), len(v)) for sec, v in by_section.items()},
    }


def _collect(config: dict) -> dict[str, dict]:
    """For each version in config: load results.json and reduce; skip missing."""
    out: dict[str, dict] = {}
    for v in config["versions"]:
        rp = lib.site_version_dir(v) / "results.json"
        if not rp.is_file():
            print(f"[summary] skip {v}: {rp} not found")
            continue
        results = json.loads(rp.read_text(encoding="utf-8"))
        out[v] = _per_version_stats(results)
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render(*, generated_at: str | None = None) -> tuple[Path, Path]:
    """Produce ``docs/summary.{txt,html}``. Returns both paths.

    ``generated_at`` (``YYYY-MM-DD``) попадает в шапку обоих файлов.
    Если не задан — берётся ``lib.today_iso()``.
    """
    config = lib.load_config()
    per_version = _collect(config)
    if not per_version:
        raise SystemExit(
            "[summary] no version has results.json yet; run ./analyze.py first"
        )

    when = generated_at or lib.today_iso()

    out_dir = lib.SITE_ROOT
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_path = out_dir / "summary.txt"
    txt_path.write_text(_render_text(per_version, config, when), encoding="utf-8")

    html_path = out_dir / "summary.html"
    html_path.write_text(_render_html(per_version, config, when), encoding="utf-8")

    print(
        f"[summary] wrote {txt_path.name} + {html_path.name} "
        f"(versions: {', '.join(per_version)})"
    )
    return txt_path, html_path


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

def _render_text(per_version: dict[str, dict], config: dict, generated_at: str) -> str:
    versions = list(per_version.keys())
    lines: list[str] = []
    lines.append("Сводка по версиям YDB docs")
    lines.append("=" * 32)
    lines.append("")
    lines.append("Источник: ydb-platform/ydb")
    lines.append(f"Сгенерировано: {generated_at}")
    lines.append("Для деталей по конкретной версии — docs/<v>/report.txt или report.html")
    lines.append("")

    # Overview table
    lines.append("Итоги по версиям:")
    header = f"  {'Версия':<8} {'Pages':>6} {'Avg':>6} {'Score=1':>8} {'Score=10':>9} {'One-lang':>9}"
    lines.append(header)
    for v in versions:
        s = per_version[v]
        lines.append(
            f"  {v:<8} {s['total']:>6} {s['avg']:>6.2f} "
            f"{s['hist'].get(1, 0):>8} {s['hist'].get(10, 0):>9} {s['single_lang']:>9}"
        )
    lines.append("")

    # Distribution matrix
    lines.append("Распределение оценок (число страниц):")
    bucket_header = "  " + " " * 8 + " ".join(f"{b:>5}" for b in range(1, 11))
    lines.append(bucket_header)
    for v in versions:
        s = per_version[v]
        cells = " ".join(
            f"{s['hist'].get(b, 0):>5}" if s['hist'].get(b, 0) else f"{'.':>5}"
            for b in range(1, 11)
        )
        lines.append(f"  {v:<8}{cells}")
    lines.append("")

    # Section heatmap
    all_sections = sorted({sec for s in per_version.values() for sec in s["by_section"]})
    lines.append("Средняя оценка по разделам:")
    width = max(28, max((len(s) for s in all_sections), default=0) + 2)
    sec_header = "  " + "Раздел".ljust(width) + " ".join(f"{v:>7}" for v in versions)
    lines.append(sec_header)
    for sec in all_sections:
        cells = []
        for v in versions:
            entry = per_version[v]["by_section"].get(sec)
            if entry is None:
                cells.append(f"{'—':>7}")
            else:
                avg, _ = entry
                cells.append(f"{avg:>7.2f}")
        lines.append(f"  {sec.ljust(width)}{' '.join(cells)}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _render_html(per_version: dict[str, dict], config: dict, generated_at: str) -> str:
    css = _build_css()
    versions = list(per_version.keys())
    all_sections = sorted({sec for s in per_version.values() for sec in s["by_section"]})

    parts = [
        "<!DOCTYPE html>\n<html lang=\"ru\">\n<head>\n",
        "<meta charset=\"utf-8\">\n",
        "<title>YDB docs sync — сводка по версиям</title>\n",
        f"<style>{css}</style>\n",
        "</head>\n<body>\n",
        "<header class=\"page-header\">\n",
        "  <h1>YDB docs sync — сводка по версиям</h1>\n",
        "  <p class=\"src\">Источник: <code>ydb-platform/ydb</code>. ",
        "Детальные отчёты — по ссылке в названии версии.</p>\n",
        f"  <p class=\"src\">Сгенерировано: <code>{html.escape(generated_at)}</code></p>\n",
        "  <p class=\"legend\">Шкала: <span class=\"badge\" style=\"",
        lib.score_badge_style(1), "\">1</span> — отсутствует или сильно расходится, ",
        "<span class=\"badge\" style=\"", lib.score_badge_style(10),
        "\">10</span> — практически идентично.</p>\n",
        "</header>\n",
    ]

    parts.append(_render_overview_block(per_version, versions))
    parts.append(_render_distribution_block(per_version, versions))
    parts.append(_render_sections_block(per_version, versions, all_sections))

    parts.append("</body>\n</html>\n")
    return "".join(parts)


def _render_overview_block(per_version: dict[str, dict], versions: list[str]) -> str:
    rows = []
    for v in versions:
        s = per_version[v]
        avg_badge = (
            f"<span class=\"badge\" style=\"{lib.score_badge_style(s['avg'])}\">"
            f"{s['avg']:.2f}</span>"
        )
        ver_link = f"<a href=\"{html.escape(v)}/report.html\">{html.escape(v)}</a>"
        rows.append(
            "<tr>"
            f"<td class=\"ver-name\">{ver_link}</td>"
            f"<td class=\"num\">{s['total']}</td>"
            f"<td>{avg_badge}</td>"
            f"<td class=\"num\">{s['hist'].get(1, 0)}</td>"
            f"<td class=\"num\">{s['hist'].get(10, 0)}</td>"
            f"<td class=\"num muted\">{s['single_lang']}</td>"
            "</tr>"
        )
    return (
        "<section class=\"card\">\n"
        "  <h2>Итоги</h2>\n"
        "  <table class=\"overview\">\n"
        "    <thead><tr>"
        "<th>Версия</th><th class=\"num\">Pages</th><th>Avg</th>"
        "<th class=\"num\">Score=1</th><th class=\"num\">Score=10</th>"
        "<th class=\"num\">One-lang</th>"
        "</tr></thead>\n"
        f"    <tbody>{''.join(rows)}</tbody>\n"
        "  </table>\n"
        "</section>\n"
    )


def _render_distribution_block(per_version: dict[str, dict], versions: list[str]) -> str:
    head_cells = "".join(
        f"<th><span class=\"badge\" style=\"{lib.score_badge_style(b)}\">{b}</span></th>"
        for b in range(1, 11)
    )
    body_rows = []
    for v in versions:
        s = per_version[v]
        cells = []
        for b in range(1, 11):
            n = s["hist"].get(b, 0)
            if n == 0:
                cells.append("<td class=\"empty\">·</td>")
            else:
                cells.append(
                    f"<td class=\"count\" style=\"{lib.score_badge_style(b)}\">{n}</td>"
                )
        ver_link = f"<a href=\"{html.escape(v)}/report.html\">{html.escape(v)}</a>"
        body_rows.append(
            f"<tr><th class=\"ver-name\">{ver_link}</th>{''.join(cells)}</tr>"
        )
    return (
        "<section class=\"card\">\n"
        "  <h2>Распределение оценок</h2>\n"
        "  <p class=\"hint\">Число страниц с конкретным баллом в каждой версии.</p>\n"
        "  <table class=\"matrix\">\n"
        f"    <thead><tr><th></th>{head_cells}</tr></thead>\n"
        f"    <tbody>{''.join(body_rows)}</tbody>\n"
        "  </table>\n"
        "</section>\n"
    )


def _render_sections_block(per_version: dict[str, dict], versions: list[str], sections: list[str]) -> str:
    head_cells = "".join(
        f"<th><a href=\"{html.escape(v)}/report.html\">{html.escape(v)}</a></th>"
        for v in versions
    )
    body_rows = []
    for sec in sections:
        cells = []
        for v in versions:
            entry = per_version[v]["by_section"].get(sec)
            if entry is None:
                cells.append("<td class=\"empty\">—</td>")
            else:
                avg, n = entry
                cells.append(
                    f"<td class=\"avg\" style=\"{lib.score_badge_style(avg)}\" title=\"{n} стр.\">"
                    f"{avg:.2f}</td>"
                )
        body_rows.append(
            f"<tr><th class=\"sec-name\">{html.escape(sec)}</th>{''.join(cells)}</tr>"
        )
    return (
        "<section class=\"card\">\n"
        "  <h2>Средняя оценка по разделам</h2>\n"
        "  <p class=\"hint\">Hover над ячейкой — число страниц в разделе для этой версии. "
        "«—» означает, что раздела в версии нет.</p>\n"
        "  <table class=\"matrix sections\">\n"
        f"    <thead><tr><th>Раздел</th>{head_cells}</tr></thead>\n"
        f"    <tbody>{''.join(body_rows)}</tbody>\n"
        "  </table>\n"
        "</section>\n"
    )


def _build_css() -> str:
    return (
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "color:#1d1d1f;background:#f6f7f9;margin:0;padding:24px 32px;line-height:1.45;}"
        "h1{margin:0 0 8px 0;font-size:22px;}"
        "h2{margin:0 0 12px 0;font-size:16px;color:#444;}"
        ".page-header{margin-bottom:20px;}"
        ".page-header .src{margin:4px 0;color:#555;font-size:13px;}"
        ".page-header .legend{margin:8px 0 0 0;color:#555;font-size:13px;}"
        ".muted{color:#888;}"
        ".card{background:#fff;border:1px solid #e1e4e8;border-radius:8px;"
        "padding:16px;margin-bottom:20px;}"
        ".card .hint{color:#666;font-size:12px;margin:0 0 12px 0;}"
        ".badge{display:inline-block;min-width:24px;padding:2px 8px;border-radius:4px;"
        "font-weight:600;font-size:12px;text-align:center;}"
        "table{border-collapse:separate;border-spacing:0;font-size:13px;}"
        "table.overview{width:100%;}"
        "table.overview th{text-align:left;color:#666;font-weight:500;"
        "padding:6px 10px;border-bottom:1px solid #e1e4e8;}"
        "table.overview td{padding:6px 10px;border-bottom:1px solid #f4f5f7;}"
        "table.overview tr:last-child td{border-bottom:none;}"
        ".num{text-align:right;font-variant-numeric:tabular-nums;}"
        ".ver-name a{color:#0969da;text-decoration:none;font-weight:600;}"
        ".ver-name a:hover{text-decoration:underline;}"
        "table.matrix{margin:0;}"
        "table.matrix th{padding:6px 10px;color:#666;font-weight:500;font-size:12px;}"
        "table.matrix thead th{text-align:center;}"
        "table.matrix tbody th{text-align:left;white-space:nowrap;}"
        "table.matrix td{padding:6px 10px;text-align:center;"
        "font-weight:600;font-variant-numeric:tabular-nums;min-width:42px;"
        "border:1px solid #fff;}"
        "table.matrix td.empty{color:#bbb;font-weight:400;background:#fafafa;}"
        "table.matrix.sections th.sec-name{font-family:ui-monospace,SFMono-Regular,"
        "'SF Mono',Menlo,monospace;font-weight:500;color:#333;padding-right:14px;}"
        "table.matrix.sections th a{color:#0969da;text-decoration:none;}"
        "table.matrix.sections th a:hover{text-decoration:underline;}"
        "code{background:#f4f5f7;padding:1px 5px;border-radius:3px;font-size:12px;}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    render()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
