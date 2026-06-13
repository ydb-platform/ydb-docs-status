#!/usr/bin/env python3
"""Compare the Russian and English documentation for a given version.

Usage::

    ./scripts/compare.py <version>

Reads the docs tree from ``cache/<version>/docs/``, pairs every
``.md`` page in ``<languages.ru>`` with its counterpart in
``<languages.en>`` (by relative path), expands ``{% include ... %}``
directives so partials don't artificially deflate the score, and writes
per-page metrics + a 1..10 similarity score into
``docs/<version>/results.json`` (where ``docs/`` is the GH Pages site root).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import lib  # type: ignore[import-not-found]


def compare(version: str) -> Path:
    """Run the comparison for ``version`` and return the results.json path."""
    config = lib.load_config()
    lib.require_version(version, config)

    docs_dir = lib.docs_root(version)
    if not docs_dir.is_dir():
        raise SystemExit(
            f"[compare] {version}: {docs_dir} not found. Run ./scripts/fetch.py {version} first."
        )

    ru_root = lib.lang_root(version, "ru", config)
    en_root = lib.lang_root(version, "en", config)
    exclude = config.get("exclude_dirs", [])

    ru_pages = {str(p): p for p in lib.collect_pages(ru_root, exclude)}
    en_pages = {str(p): p for p in lib.collect_pages(en_root, exclude)}
    all_rel = sorted(set(ru_pages) | set(en_pages))
    slx_patterns = config.get("single_language_patterns", [])

    print(f"[compare] {version}: ru={len(ru_pages)}, en={len(en_pages)}, union={len(all_rel)}")

    results = []
    for rel in all_rel:
        ru_file = ru_root / rel if rel in ru_pages else None
        en_file = en_root / rel if rel in en_pages else None
        ru_m = _metrics_for(ru_file, docs_dir) if ru_file else None
        en_m = _metrics_for(en_file, docs_dir) if en_file else None
        results.append({
            "rel": rel,
            "ru_exists": ru_file is not None,
            "en_exists": en_file is not None,
            "single_language_expected": lib.is_single_language_expected(rel, slx_patterns),
            "ru_metrics": ru_m.as_dict() if ru_m else None,
            "en_metrics": en_m.as_dict() if en_m else None,
            "score": lib.score(ru_m, en_m),
        })

    out_path = lib.site_version_dir(version) / "results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[compare] {version}: wrote {out_path} ({len(results)} pages)")
    return out_path


def _metrics_for(file_path: Path, docs_dir: Path) -> lib.PageMetrics:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    text = lib.expand_includes(text, file_path.parent, docs_dir)
    return lib.metrics(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="version key from config.json (e.g. 25.3)")
    args = parser.parse_args(argv)
    compare(args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
