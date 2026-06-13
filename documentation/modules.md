# Module reference

The top-level entry points (`download.py`, `analyze.py`) are thin
orchestrators. All logic lives under `scripts/`. `lib.py` is the
shared module everything else imports.

## Entry points (top level)

### `download.py`

CLI: `./download.py [<version>...] [--refresh]`.

Adds `scripts/` to `sys.path`, reads `config.json`, calls
`fetch.fetch(v, refresh=...)` for each requested version (or for all
of them). Fetched content lands at `cache/<v>/docs/`.

### `analyze.py`

CLI: `./analyze.py [<version>...]`.

Computes today's date → `archive.archive_previous(today)` → for each
version, calls `compare.compare(v)` and
`report.render(v, generated_at=today)`; then unconditionally calls
`summary.render(generated_at=today)`, `index.render_landing(today, ...)`,
`index.render_history_index(...)`, and writes `docs/meta.json` with
today's date. No network — all input comes from `cache/<v>/docs/`.
If the docs aren't fetched yet for some version, `compare` fails with
a clear message asking you to run `./download.py <v>` first.

## `scripts/lib.py`

### Paths and config

| Function / constant | Purpose |
| --- | --- |
| `PROJECT_ROOT` | Project root, derived from `__file__`. |
| `CACHE_ROOT` | `cache/` — root of fetched docs (gitignored). |
| `SITE_ROOT` | `docs/` — root of the GH Pages site (committed). |
| `HISTORY_ROOT` | `docs/history/` — archive of previous snapshots. |
| `load_config()` | Reads `config.json`. |
| `cache_version_dir(v)` | `cache/<v>/`. |
| `site_version_dir(v)` | `docs/<v>/` — current per-version report. |
| `history_dir(date)` | `docs/history/<date>/`. |
| `docs_root(v)` | `cache/<v>/docs/` — `ydb/docs` subtree for the version. |
| `lang_root(v, lang, cfg)` | Language root inside `docs/` (e.g. `.../ru/core`). |
| `require_version(v, cfg)` | Raises `SystemExit` with a clear message if the version is unknown. |
| `today_iso()` | `YYYY-MM-DD` for `generated_at` and snapshot folder names. |

### Page collection

`collect_pages(lang_root_path, exclude_dirs) -> list[Path]` — walks
the tree and returns relative paths of `.md` files, skipping any whose
path contains an `exclude_dirs` segment.

### Single-language pages

`is_single_language_expected(rel_path, patterns) -> bool` — True if
the relative path matches any of `patterns`. Uses fnmatch globs
(`*` matches `/` too, so `public-materials/*` catches any depth). See
[scoring.md](scoring.md#pages-outside-scoring) and
[howto.md](howto.md#single-language-pages).

### Include expansion

`expand_includes(text, base_dir, docs_dir, depth=0) -> str` recursively
expands `{% include ... %}`:

- `{% include path %}` — path relative to `base_dir`;
- `{% include [title](path) %}` — same;
- a path starting with `/` is resolved relative to `docs_dir`.

Depth is capped at 4. Missing includes expand to an empty string (no
crash).

### Metrics

`metrics(text) -> PageMetrics` — structural features:
`lines`, `headings_total`, `h1`, `h2`, `h3`, `code_blocks`, `links`,
`images`, `chars`, `words`.

`PageMetrics.as_dict()` — serialization for `results.json`.

### Score

`score(ru: PageMetrics|None, en: PageMetrics|None) -> float` — 1..10.
Weights come from `SCORE_WEIGHTS`. Details in [scoring.md](scoring.md).

### URL

`page_to_url(lang, rel_path, url_version, url_base=...)` — public URL
for a page. `index.md` is stripped; `url_version=None` drops the
`?version=` query parameter.

### Score and palette (for reports)

`SCORE_COLORS: dict[int, tuple[str, str]]` — RdYlGn palette 1..10,
format `{score: (background_hex, text_hex)}`. Used by both report
renderers (`report.py` and `summary.py`).

`int_score(result_dict) -> int` — rounds `result["score"]` to an
integer 1..10. Pages where `ru_exists` or `en_exists` is False always
collapse to 1.

`score_badge_style(score_value: int | float) -> str` — inline CSS
`background:..;color:..;` for a badge. Accepts a float (the summary
uses averages) and rounds for the color lookup.

## `scripts/fetch.py`

CLI: `./scripts/fetch.py <version> [--refresh]`.

Public function: `fetch(version: str, *, refresh: bool=False) -> Path`.

Sparse-checks-out `sparse_paths` from branch `versions[version].ref`
into a temp directory, then moves `ydb/docs` into `cache/<v>/docs/`.

## `scripts/compare.py`

CLI: `./scripts/compare.py <version>`.

Public function: `compare(version: str) -> Path` (returns the
`results.json` path).

Pairs files by relative path under `lang_root`. The union of the ru/en
sets ensures pages existing on only one side still make it into the
report with a marker. Output: `docs/<v>/results.json`.

## `scripts/report.py`

CLI: `./scripts/report.py <version>`.

Public function: `render(version: str, *, generated_at: str | None = None)
-> tuple[Path, Path]` — returns the paths of `report.txt` and
`report.html`. If `generated_at` is not provided, `lib.today_iso()` is
used. The date appears in the header of both files ("Generated: …").

Steps:

1. `_build_rows(results, url_version, url_base)` — shared structure
   for both formats; builds ru/en URLs and splits rows into the main
   table and the "expected single-language" set (rows where
   `single_language_expected` exists on only one side).
2. `_render_text(...)` — compact text with two columns (score + ru
   URL), histogram, by-section breakdown.
3. `_render_html(...)` — self-contained HTML; color badges come from
   `lib.SCORE_COLORS` (RdYlGn palette). CSS inlined, no external
   resources.

Change the palette in `lib.SCORE_COLORS`; HTML styling in `_build_css`
inside `report.py` (or `summary.py` for the cross-version view).

## `scripts/summary.py`

CLI: `./scripts/summary.py` (no arguments).

Public function: `render(*, generated_at: str | None = None) ->
tuple[Path, Path]` — returns the paths of `docs/summary.txt` and
`docs/summary.html`. Default `generated_at` is `lib.today_iso()`.

Steps:

1. `_collect(config)` — for each version in the config, tries to read
   `docs/<v>/results.json`. If the file is missing, that version is
   skipped with a warning (no crash).
2. `_per_version_stats(results)` — private reducer: computes `total`,
   `avg`, `hist`, `by_section` (`{section: (avg, n)}`), `single_lang`.
   Logic is aligned with `report.py` (single-language pages without a
   translation are excluded).
3. `_render_text(...)` — totals table, distribution matrix (version ×
   bucket), sections table (section × version).
4. `_render_html(...)` — same content in HTML with colored cells;
   version names link to per-version `report.html` (relative path
   `<version>/report.html`). Header includes "Generated: …".

CSS is inlined. The palette comes from `lib.SCORE_COLORS`, so a color
change in one place propagates to both per-version and summary
reports.

## `scripts/archive.py`

CLI: `./scripts/archive.py [<today>]`.

Public function:
`archive_previous(today: str | None = None) -> str | None`.

Algorithm:

1. If `docs/meta.json` is missing → `None` (nothing to archive).
2. If `meta["generated_at"] == today` → `None` (same-day re-run; the
   current folder will just be overwritten).
3. Otherwise re-create `docs/history/<old_date>/` and copy everything
   under `docs/` except `history/` and `index.html` into it.

Returns the old snapshot date. `index.html` is excluded from the
archive because each snapshot already has its own `summary.html` as a
self-contained entry point; the snapshot list is rendered separately
into `docs/history/index.html`.

## `scripts/index.py`

CLI: `./scripts/index.py [<generated_at>]` (default: today).

Public functions:

- `history_dates() -> list[str]` — subfolder names of `docs/history/`
  in reverse chronological order (names are `YYYY-MM-DD`, so lex
  order equals chronological order).
- `render_landing(generated_at: str | None = None, dates: list[str] |
  None = None) -> Path` — renders `docs/index.html`: title, last-run
  date, link to `summary.html`, up to 5 most recent history dates
  inline, link to the full index.
- `render_history_index(dates: list[str] | None = None) -> Path` —
  renders `docs/history/index.html`: list of links to
  `<date>/summary.html`.

CSS is inlined in `_css()`; the files are self-contained.

## Conventions

- All CLIs emit `[stage] <version>: ...` lines — easy to grep through
  `analyze.py` logs.
- Failures use `raise SystemExit(...)` with a plain-English user
  message; internal bugs use regular exceptions.
- No third-party dependencies. Just the Python standard library and
  `git`.
- Imports between scripts: `download.py` and `analyze.py` add
  `scripts/` to `sys.path` and use `import lib`, `import fetch as fetch_mod`,
  etc. Inside `scripts/*.py`, modules import each other by short name
  (`import lib`).
