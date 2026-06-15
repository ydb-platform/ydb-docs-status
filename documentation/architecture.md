# Architecture

## Goal

Get a quantitative picture of how the Russian and English versions of the
YDB documentation diverge across product versions. The source of truth is
the markdown under [`ydb-platform/ydb`](https://github.com/ydb-platform/ydb)
in the `ydb/docs/` subtree. The resulting reports are published as a
GitHub Pages site served from the `docs/` directory.

## Project tree

```
ydb_ru_eng_sync/
├── README.md
├── CLAUDE.md
├── .gitignore                  # excludes cache/
├── config.json                 # version registry and shared settings
├── download.py                 # TOP LEVEL: fetch docs for every version into cache/
├── analyze.py                  # TOP LEVEL: archive + compare + report + summary + index
├── scripts/                    # implementation (imported by the entry points)
│   ├── lib.py                  # shared helpers and constants (paths, metrics, palette)
│   ├── fetch.py                # sparse-checkout of ydb/docs for one version into cache/
│   ├── compare.py              # pairwise metrics + score → docs/<v>/results.json
│   ├── report.py               # results.json → docs/<v>/report.{txt,html}
│   ├── summary.py              # cross-version summary → docs/summary.{txt,html}
│   ├── archive.py              # snapshot of current docs/ → docs/history/<old_date>/
│   └── index.py                # landing docs/index.html + docs/history/index.html
├── documentation/              # internal Markdown about THIS project
├── cache/                      # (gitignored) fetched YDB docs per version
│   └── <version>/
│       └── docs/               # contents of ydb/docs from the version branch
│           ├── _includes/      # shared partials (matter for compare)
│           ├── _assets/
│           ├── ru/core/...     # Russian pages
│           └── en/core/...     # English pages
└── docs/                       # COMMITTED — GH Pages site root
    ├── meta.json               # {"generated_at": "YYYY-MM-DD"} of the last run
    ├── index.html              # landing (site entry point)
    ├── summary.{txt,html}      # current cross-version summary
    ├── <version>/              # current per-version report
    │   ├── results.json        # machine-readable pairwise metrics
    │   ├── report.txt          # compact text (for grep / diff)
    │   └── report.html         # interactive browser report
    └── history/
        ├── index.html          # list of snapshots (reverse chronological)
        └── <YYYY-MM-DD>/       # site snapshot taken on that date
            ├── meta.json
            ├── summary.{txt,html}
            └── <version>/...
```

### Two "docs" at the root — don't confuse them

| Folder | Purpose |
| --- | --- |
| `docs/` | Generated HTML site, root of GitHub Pages. Committed. |
| `documentation/` | Internal Markdown for developers. Committed, but not part of the public site. |

The name `docs/` is fixed by the GitHub Pages convention in *Deploy from
a branch* mode: only the repo root and `/docs` are servable. Changing
that would require switching to an Actions-based workflow.

`cache/` is excluded from git entirely (see `.gitignore`): fetched docs
are heavy (~100 MB per version) and fully derived, rebuilt via
`./download.py`.

## Entry points

Two top-level scripts:

| Script          | What it does                                          |
| --------------- | ----------------------------------------------------- |
| `./download.py` | Sparse-checkout `ydb/docs` for every version in the config into `cache/<v>/ydb/docs/`. Network operation. Incrementally updates an existing clone via `git fetch`. |
| `./analyze.py`  | Archive the previous snapshot → per version: `compare` → `report`; then `summary` + `index`; write `docs/meta.json`. No network. |

Both accept an optional list of versions and `--help`. Real logic lives
under `scripts/`; the entry points are thin orchestrators (~30 lines)
that add `scripts/` to `sys.path` and call the public functions in each
module.

## Data flow

```
docs/meta.json
    │
    ▼
archive.py — if generated_at ≠ today, copy everything in
             docs/* (except history/ and index.html)
             into docs/history/<old_date>/

config.json
    │
    ▼
fetch.py  ──── git clone --sparse ─── ydb-platform/ydb
    │                                         │
    │                                         └── ydb/docs/
    ▼
cache/<v>/ydb/docs/   (`.git/` lives at cache/<v>/)
    │
    ▼
compare.py
    │  ─ collect_pages(ru/core)     ┐
    │  ─ collect_pages(en/core)     │
    │  ─ pair by relative path      │
    │  ─ expand_includes (docs root)│
    │  ─ metrics + score            │
    ▼                               ▼
docs/<v>/results.json
    │
    ▼
report.py
    │  ─ score → int (1..10)
    │  ─ page_to_url for ru and en (with ?version=)
    │  ─ sort, histogram, by-section breakdown
    │  ─ separate section for "expected single-language pages"
    │  ─ generated_at stamp in the header (txt + html)
    ▼
docs/<v>/report.txt + report.html
    │
    │  (after every version is processed)
    ▼
summary.py — reads every docs/<v>/results.json
    ▼
docs/summary.txt + summary.html (generated_at in the header)
    │
    ▼
index.py — list of dates from docs/history/, landing render
    ▼
docs/index.html + docs/history/index.html
    │
    ▼
write docs/meta.json = {"generated_at": today}
```

### HTML report

Self-contained file (all CSS inlined, no external dependencies):

- Header: version, source, generation date, scale legend.
- Stats block: score distribution and by-section averages.
- Main table: score (colored badge from the RdYlGn palette), page path,
  and two link columns — RU and EN. A missing side shows an em-dash.
- "Expected single-language pages" block: compact list with a link to
  the existing language and an `RU-only` / `EN-only` tag.

The color palette is defined in `scripts/lib.py` via the `SCORE_COLORS`
constant — a dict `{score → (background, text)}`. Changing it there
updates both `report.html` and `summary.html`.

### Cross-version summary

`scripts/summary.py` aggregates every `docs/<v>/results.json` and
produces:

- `docs/summary.txt` — overview table, score distribution matrix
  (version × bucket), and average-score table (section × version).
  Generation date in the header.
- `docs/summary.html` — same content, interactive: matrix cells
  colored from `SCORE_COLORS`, version names clickable links to the
  per-version `report.html`. A useful follow-up to the landing page.

Versions without a `results.json` are skipped with a warning.
`analyze.py` calls `summary.render()` at the end of every run, so the
summary always reflects whatever is on disk.

### Landing and history index

`scripts/index.py` renders two HTML pages:

- `docs/index.html` — site entry point: title, last-run date, link to
  `summary.html`, a short list of recent history dates inline, and a
  link to the full history index.
- `docs/history/index.html` — reverse-chronological list of all
  snapshots; every link points to `<date>/summary.html`.

Both are self-contained, CSS inlined, no external resources.

### Snapshot archive

`scripts/archive.py` reads `docs/meta.json` and, if the date recorded
there differs from today, copies everything under `docs/` (except
`history/` itself and `index.html`) into `docs/history/<old_date>/`.
Each snapshot keeps its own `meta.json` and `summary.{txt,html}` — a
snapshot can be opened and read independently.

A same-day re-run is a no-op for the archive (the new reports simply
overwrite the current files). To rebuild an archive by hand, edit
`docs/meta.json` (set an old date) and run `./analyze.py`.

## Configuration (`config.json`)

| Field          | Purpose                                                     |
| -------------- | ----------------------------------------------------------- |
| `repo`         | URL of the YDB git repository.                              |
| `sparse_paths` | Paths passed to `git sparse-checkout set`.                  |
| `languages`    | Mapping from language code to the root inside `ydb/docs`.   |
| `exclude_dirs` | Folders whose contents are NOT treated as standalone pages. |
| `single_language_patterns` | fnmatch globs of relative page paths that exist on one language **by design** (e.g. `public-materials/*`). These pages don't get a score of 1 "missing translation"; they go into a separate report section. See [howto.md](howto.md#single-language-pages). |
| `url_base`     | Base URL of the public documentation.                       |
| `versions`     | Map `<version> → {ref, url_version}`.                       |

YDB-side directory tweaks can be expressed in the config without code
changes.

## What's in `results.json`

An array of objects:

```json
{
  "rel": "concepts/transactions.md",
  "ru_exists": true,
  "en_exists": true,
  "single_language_expected": false,
  "ru_metrics": { "lines": 119, "headings_total": 8, "h1": 1, ... },
  "en_metrics": { "lines": 109, "headings_total": 8, "h1": 1, ... },
  "score": 9.72
}
```

`single_language_expected: true` means the path matches one of the
patterns under `single_language_patterns` (see
[howto.md](howto.md#single-language-pages)). If such a page exists on
only one language, that's expected and it is not in the main report.

`score` is a float in `[1.0, 10.0]`; in `report.txt` it is rounded to
an integer. If a page is missing on one side, both metrics objects can
be `null` and `score` is guaranteed to be 1.

The generation date is NOT duplicated into `results.json`: the single
source of truth is `docs/meta.json`.

## Idempotency and caching

- `fetch.py` updates already-fetched versions incrementally: it runs
  `git fetch --depth=1 origin <ref> && git reset --hard FETCH_HEAD` on
  the existing clone at `cache/<v>/`. With `--refresh`, the whole
  `cache/<v>/` directory is wiped and re-cloned. A cache directory left
  over from the old layout (no `.git/` inside) is detected and replaced
  by a fresh clone on first run.
- `compare.py`, `report.py`, `summary.py`, `index.py` always overwrite
  their outputs.
- `archive.py` is a no-op when `docs/meta.json` is missing or its
  `generated_at` already matches today.
- No global state outside `cache/`, `docs/`, and `config.json`.
