# ydb_ru_eng_sync

Compares the Russian and English versions of the [YDB](https://ydb.tech)
documentation across multiple product versions. Each page gets a score
from 1 to 10: 1 means the page is missing on one side or differs sharply,
10 means the two versions are nearly identical.

Generated reports are published to GitHub Pages (see below).

## Requirements

- Python 3.10+
- `git` 2.25+ (needs `sparse-checkout` and `--filter=blob:none`)
- Outbound internet access to `github.com`

## Quick start

```bash
./download.py     # fetch docs for every version from ydb-platform/ydb into cache/
./analyze.py      # compare ru/en, build reports under docs/
```

Open the result locally:

```bash
open docs/index.html             # landing: links to summary and history
open docs/summary.html           # convenient entry point: all versions
open docs/main/report.html       # per-version detail
```

If you change the methodology (weights, patterns), no network is needed:

```bash
./analyze.py      # recompute against the docs already in cache/
```

## What's in the repository

```
ydb_ru_eng_sync/
├── README.md
├── CLAUDE.md
├── config.json                 # version registry and shared settings
├── download.py                 # entry point: fetch docs into cache/
├── analyze.py                  # entry point: archive → compare → report → summary → index
├── scripts/                    # implementation (fetch, compare, report, summary, archive, index, lib)
├── documentation/              # internal project docs (for developers)
├── cache/                      # (gitignored) fetched YDB docs
└── docs/                       # COMMITTED — root of the GH Pages site
    ├── index.html              # landing
    ├── summary.{html,txt}      # current cross-version summary
    ├── <v>/                    # current per-version report
    └── history/<YYYY-MM-DD>/   # archive of previous snapshots
```

Two "docs" folders at the root — they are not duplicates:

| Folder | Contents |
| --- | --- |
| `docs/` | Generated HTML site, root of GitHub Pages. **Committed.** |
| `documentation/` | Internal Markdown about the project (architecture, recipes, module reference) — read by humans, not published. |

The heavy fetched `cache/<v>/docs/` (~100 MB × N versions) is excluded
by `.gitignore` and rebuilt by `./download.py`.

## Report history

`docs/meta.json` stores the date of the last run. On every
`./analyze.py` run:

1. If the date in `meta.json` differs from today, the current snapshot
   under `docs/` (excluding `history/` and `index.html`) is copied into
   `docs/history/<old_date>/`.
2. `docs/<v>/...`, `docs/summary.*`, and `docs/index.html` are
   regenerated.
3. `docs/meta.json` is rewritten with the new date.

Multiple runs in the same day overwrite that day's folder — only the
last snapshot of the day is kept. Every report (`summary.html`,
`<v>/report.html`) carries a "Generated: …" line in its header.

## Team workflow

For any team member:

```bash
git pull
./download.py            # pull updates (mainly main and stable-*)
./analyze.py             # rebuild reports
git add docs             # docs/ is committed; cache/ is not
git commit -m "docs: snapshot $(date +%Y-%m-%d)"
git push
```

After the push, GitHub Pages refreshes the site automatically (see below).

To see exactly what changed in the reports:

```bash
git diff --stat docs/
git diff docs/summary.txt    # the txt variants are easy to review via git diff
```

## GitHub Pages

One-time setup for the repository owner:

1. **Settings → Pages**.
2. **Source**: *Deploy from a branch*.
3. **Branch**: `main`, **Folder**: `/docs`.
4. Save.

No GitHub Actions involved — Pages serves the contents of `docs/`
directly from the `main` branch. The site URL appears in the same
settings page.

## Add a new YDB version

1. Open [`config.json`](config.json) and add an entry under `"versions"`:
   ```json
   "26.2": {"ref": "stable-26-2", "url_version": "v26.2"}
   ```
2. Run:
   ```bash
   ./download.py 26.2
   ./analyze.py
   ```

## Fine-tuning

- `./download.py <v>...` / `./analyze.py <v>...` — work on a subset of versions.
- `./download.py --refresh <v>` — force re-fetch (needed when `main` moves or `stable-*` gets a hotfix).
- The individual stages can be called directly via `scripts/fetch.py`,
  `scripts/compare.py`, `scripts/report.py`, `scripts/summary.py`,
  `scripts/archive.py`, `scripts/index.py` — each has `--help`.

## Project documentation

- [documentation/architecture.md](documentation/architecture.md) — system layout, data flow.
- [documentation/scoring.md](documentation/scoring.md) — scoring methodology, weights, limitations.
- [documentation/howto.md](documentation/howto.md) — common recipes.
- [documentation/modules.md](documentation/modules.md) — function- and module-level reference.
