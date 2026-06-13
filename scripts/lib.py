"""Shared utilities for the YDB docs ru/en comparison pipeline.

This module centralises everything the CLI scripts (fetch / compare /
report / run_all) need: config loading, path layout, include expansion,
content metrics, similarity scoring, and URL construction.

The pipeline never modifies the cloned YDB docs; it only reads them.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Скачанные YDB docs всех версий. Gitignored, ~100 МБ × N версий.
CACHE_ROOT = PROJECT_ROOT / "cache"

#: Корень публикуемого сайта GH Pages. Коммитится в репозиторий.
SITE_ROOT = PROJECT_ROOT / "docs"

#: Архив прошлых снимков сайта (по дате генерации).
HISTORY_ROOT = SITE_ROOT / "history"


def load_config(root: Path = PROJECT_ROOT) -> dict:
    """Read ``config.json`` from the project root and return it as a dict."""
    return json.loads((root / "config.json").read_text(encoding="utf-8"))


def cache_version_dir(version: str) -> Path:
    """Return ``cache/<version>/`` — где живут скачанные docs YDB для версии."""
    return CACHE_ROOT / version


def site_version_dir(version: str) -> Path:
    """Return ``docs/<version>/`` — корень сгенерированных отчётов версии."""
    return SITE_ROOT / version


def history_dir(date_str: str) -> Path:
    """Return ``docs/history/<date>/`` — снимок сайта от данной даты."""
    return HISTORY_ROOT / date_str


def docs_root(version: str) -> Path:
    """Return ``cache/<version>/docs/`` — поддерево ``ydb/docs`` версии."""
    return cache_version_dir(version) / "docs"


def lang_root(version: str, lang: str, config: dict) -> Path:
    """Return ``cache/<version>/docs/<languages[lang]>/`` from config.

    Example: ``lang_root("25.3", "ru", cfg)`` →
    ``cache/25.3/docs/ru/core``.
    """
    sub = config["languages"][lang]
    return docs_root(version) / sub


def today_iso() -> str:
    """Return today's date in ``YYYY-MM-DD`` for ``generated_at`` stamps."""
    return date.today().isoformat()


def require_version(version: str, config: dict) -> dict:
    """Validate that ``version`` exists in config and return its entry."""
    versions = config.get("versions", {})
    if version not in versions:
        known = ", ".join(sorted(versions)) or "<none>"
        raise SystemExit(
            f"Unknown version '{version}'. Known versions: {known}.\n"
            f"Add it to config.json to enable."
        )
    return versions[version]


# ---------------------------------------------------------------------------
# Page collection
# ---------------------------------------------------------------------------

def collect_pages(lang_root_path: Path, exclude_dirs: Iterable[str]) -> list[Path]:
    """Return all ``.md`` page paths under ``lang_root_path`` (relative).

    Files whose path contains any of ``exclude_dirs`` as a segment are
    skipped. This filters out partials (``_includes``) and assets
    (``_assets``), which are not standalone pages.
    """
    excluded = set(exclude_dirs)
    pages: list[Path] = []
    for path in sorted(lang_root_path.rglob("*.md")):
        if any(part in excluded for part in path.parts):
            continue
        pages.append(path.relative_to(lang_root_path))
    return pages


# ---------------------------------------------------------------------------
# Single-language exclusions
# ---------------------------------------------------------------------------

def is_single_language_expected(rel_path: str, patterns: Iterable[str]) -> bool:
    """Return True if ``rel_path`` matches any ``single_language_patterns``.

    Patterns use ``fnmatch`` semantics — ``*`` matches any character
    including path separators. So ``public-materials/*`` covers any depth
    under ``public-materials/`` (e.g. ``public-materials/publications/2023.md``).

    These pages are intentionally one-language only (e.g. publications and
    talks recorded in a single natural language) and should not be flagged
    as «missing translation».
    """
    return any(fnmatch(rel_path, p) for p in patterns)


# ---------------------------------------------------------------------------
# Include expansion
# ---------------------------------------------------------------------------

_INCLUDE_RE = re.compile(r"\{%\s*include\s+([^%]*?)\s*%\}")
_MD_LINK_RE = re.compile(r"\(([^)]+)\)")


def expand_includes(text: str, base_dir: Path, docs_dir: Path, depth: int = 0) -> str:
    """Recursively expand ``{% include ... %}`` directives in markdown text.

    Supports the two forms used in the YDB docs:

      * ``{% include [some title](path/to/file.md) %}`` (with optional
        ``notitle`` prefix);
      * ``{% include path/to/file.md %}``.

    Paths starting with ``/`` are resolved relative to ``docs_dir``
    (the root of the YDB docs tree for the current version). Other
    paths are resolved relative to ``base_dir`` (the directory of the
    including file). Missing or unreadable includes expand to an empty
    string so that downstream metrics stay defined.

    ``depth`` guards against include cycles (capped at 4 levels).
    """
    if depth > 4:
        return text

    def repl(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        md = _MD_LINK_RE.search(body)
        inc_path = md.group(1).strip() if md else body.strip().strip('"').strip("'")
        if inc_path.startswith("/"):
            candidate = docs_dir / inc_path.lstrip("/")
        else:
            candidate = base_dir / inc_path
        if not candidate.is_file():
            return ""
        try:
            inner = candidate.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""
        return expand_includes(inner, candidate.parent, docs_dir, depth + 1)

    return _INCLUDE_RE.sub(repl, text)


def strip_frontmatter(text: str) -> str:
    """Remove leading YAML frontmatter (``---`` block) if present."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :]
    return text


# ---------------------------------------------------------------------------
# Metrics & scoring
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PageMetrics:
    """Structural features of a markdown page, used as a similarity proxy."""

    lines: int
    headings_total: int
    h1: int
    h2: int
    h3: int
    code_blocks: int
    links: int
    images: int
    chars: int
    words: int

    def as_dict(self) -> dict:
        return {
            "lines": self.lines,
            "headings_total": self.headings_total,
            "h1": self.h1,
            "h2": self.h2,
            "h3": self.h3,
            "code_blocks": self.code_blocks,
            "links": self.links,
            "images": self.images,
            "chars": self.chars,
            "words": self.words,
        }


_HEADING_RE = re.compile(r"^(#{1,6})\s")


def metrics(text: str) -> PageMetrics:
    """Compute structural metrics for a piece of markdown.

    Frontmatter is stripped first so it doesn't pollute the counts.
    """
    text = strip_frontmatter(text)
    lines = text.splitlines()
    heading_levels = [len(m.group(1)) for m in (_HEADING_RE.match(l) for l in lines) if m]
    code_blocks = len(re.findall(r"```", text)) // 2
    return PageMetrics(
        lines=len(lines),
        headings_total=len(heading_levels),
        h1=sum(1 for lvl in heading_levels if lvl == 1),
        h2=sum(1 for lvl in heading_levels if lvl == 2),
        h3=sum(1 for lvl in heading_levels if lvl == 3),
        code_blocks=code_blocks,
        links=len(re.findall(r"\]\(", text)),
        images=len(re.findall(r"!\[", text)),
        chars=len(re.sub(r"\s+", "", text)),
        words=len(re.findall(r"\S+", text)),
    )


# Weights used by ``score``. Sum must be 1.0. Kept close to the original
# ad-hoc weights so the v25.3 distribution stays comparable.
SCORE_WEIGHTS = {
    "headings_total": 0.25,
    "words": 0.20,
    "chars": 0.10,
    "code_blocks": 0.20,
    "links": 0.15,
    "images": 0.10,
}


def _ratio(a: int, b: int) -> float:
    if a == 0 and b == 0:
        return 1.0
    if a == 0 or b == 0:
        return 0.0
    return min(a, b) / max(a, b)


def score(ru: PageMetrics | None, en: PageMetrics | None) -> float:
    """Combine per-feature ratios into a 1..10 similarity score.

    Returns 1.0 when either side is missing. See ``documentation/scoring.md``
    for the reasoning behind the weights and the known limitations of this
    structural proxy.
    """
    if ru is None or en is None:
        return 1.0
    ru_d = ru.as_dict()
    en_d = en.as_dict()
    weighted = sum(_ratio(ru_d[k], en_d[k]) * w for k, w in SCORE_WEIGHTS.items())
    return round(1 + weighted * 9, 2)


# ---------------------------------------------------------------------------
# Score → integer + colour palette (shared between report and summary)
# ---------------------------------------------------------------------------

#: RdYlGn-style palette from red (1) to green (10). Foreground colour is
#: chosen so text on top of the background stays readable.
SCORE_COLORS: dict[int, tuple[str, str]] = {
    1:  ("#a50026", "#ffffff"),
    2:  ("#b51e29", "#ffffff"),
    3:  ("#d73027", "#ffffff"),
    4:  ("#f46d43", "#ffffff"),
    5:  ("#fdae61", "#222222"),
    6:  ("#fee08b", "#222222"),
    7:  ("#d9ef8b", "#222222"),
    8:  ("#a6d96a", "#222222"),
    9:  ("#66bd63", "#ffffff"),
    10: ("#1a9850", "#ffffff"),
}


def int_score(result: dict) -> int:
    """Round a ``results.json`` entry to an integer 1..10 score.

    Missing-on-one-side pages always collapse to 1.
    """
    if not result["ru_exists"] or not result["en_exists"]:
        return 1
    return max(1, min(10, round(result["score"])))


def score_badge_style(score_value: int | float) -> str:
    """Return the inline CSS (``background:..;color:..;``) for a score badge.

    Accepts integer scores 1..10. Floats are rounded for colour lookup but
    the caller decides what value to display in the badge.
    """
    key = max(1, min(10, round(score_value)))
    bg, fg = SCORE_COLORS[key]
    return f"background:{bg};color:{fg};"


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

def page_to_url(
    lang: str,
    rel_path: Path | str,
    url_version: str | None,
    url_base: str = "https://ydb.tech/docs",
) -> str:
    """Build the public URL for a doc page.

    ``rel_path`` is the page path relative to the language root
    (``ydb/docs/<lang>/core/``). ``index.md`` segments are stripped from
    the URL (the YDB site serves a directory listing for those). The
    ``url_version`` is appended as ``?version=<value>``; pass ``None`` to
    omit the query parameter entirely.
    """
    rel = str(rel_path).replace("\\", "/")
    if rel.endswith("/index.md"):
        rel = rel[: -len("/index.md")]
    elif rel == "index.md":
        rel = ""
    elif rel.endswith(".md"):
        rel = rel[: -len(".md")]
    url = f"{url_base}/{lang}"
    if rel:
        url += "/" + rel
    if url_version:
        url += f"?version={url_version}"
    return url
