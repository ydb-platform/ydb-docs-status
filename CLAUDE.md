# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Compares the Russian and English versions of YDB documentation
([ydb-platform/ydb](https://github.com/ydb-platform/ydb), subtree `ydb/docs/`)
across multiple product versions. For each page pair, a structural score
1..10 is computed (1 = missing or sharply diverged, 10 = structurally
identical) and rendered as per-version reports plus a cross-version summary.

Generated reports are published as a GitHub Pages site served from the
`docs/` directory of the repo.

Note: user-facing strings (CLI output, error messages, project documentation) are in Russian. Match this convention when editing existing messages; new internal code/comments don't need to be Russian.

## Commands

```bash
./download.py                   # sparse-checkout docs for all versions in config.json → cache/
./download.py 25.3 main         # subset
./download.py --refresh main    # force re-download (main moves; stable-* gets hotfixes)

./analyze.py                    # archive previous snapshot, compare + per-version reports + summary + index
./analyze.py 25.3               # just one version (summary + index still rebuilt at end)

./scripts/fetch.py <v>          # single stage; each script has --help
./scripts/compare.py <v>
./scripts/report.py <v>
./scripts/summary.py            # no args; reads every docs/<v>/results.json
./scripts/archive.py            # snapshot current docs/ into docs/history/<old_date>/
./scripts/index.py              # rebuild docs/index.html + docs/history/index.html
```

No build, no lint, no test suite — pure stdlib Python 3.10+ and `git` 2.25+ (needs `sparse-checkout` and `--filter=blob:none`). No third-party dependencies.

## Architecture

Top-level `download.py` and `analyze.py` are ~30-line orchestrators that prepend `scripts/` to `sys.path` and call public functions in `scripts/*.py`. Real logic lives in `scripts/`. Inside `scripts/`, modules import each other by short name (`import lib`, `import compare`, etc.) — do NOT change this to package-style imports without also fixing the entry-point shims.

Pipeline (per `./analyze.py` run):

```
docs/meta.json    →  archive.py     →  copy current docs/ snapshot to docs/history/<old_date>/
                                       (only if meta.json's generated_at ≠ today)
config.json + cache/<v>/docs/
                  →  compare.py     →  docs/<v>/results.json   (per version)
                  →  report.py      →  docs/<v>/report.{txt,html}
After all versions:
                  →  summary.py     →  docs/summary.{txt,html}
                  →  index.py       →  docs/index.html + docs/history/index.html
                  →  write docs/meta.json with today's date
```

`download.py` is independent and lands docs at `cache/<v>/docs/`. The `analyze.py` orchestrator always rebuilds the summary and landing pages at the end, so the cross-version view always reflects whatever `results.json` files are on disk (versions with no `results.json` yet are skipped with a warning, not an error).

### Two «docs» directories — don't confuse them

| Directory | Role |
| --- | --- |
| `docs/` | Generated HTML site, root of GitHub Pages. **Committed**, served from `main` branch. |
| `documentation/` | Project's own internal markdown (architecture, recipes, module reference). **Committed**, not part of the public site. |

The name `docs/` is required because GitHub Pages "Deploy from a branch" mode only serves from repo root or `/docs`. Renaming would require switching to a GitHub Actions workflow.

### Single source of truth: `config.json`

Adding a YDB version requires **no code change** — only a new entry under `"versions"` (`ref` = git branch, `url_version` = public URL segment). Same for `single_language_patterns` (fnmatch globs for pages that exist on one language by design, e.g. `public-materials/*`) and `exclude_dirs`. If you find yourself special-casing a path in code, check whether it should be a config entry instead.

### Single source of truth: `scripts/lib.py`

Cross-cutting constants live in `lib.py` and are imported by both `report.py` and `summary.py`. Changing them in one place updates both renderers:

- `CACHE_ROOT`, `SITE_ROOT`, `HISTORY_ROOT` — top-level paths.
- `cache_version_dir(v)` / `site_version_dir(v)` / `history_dir(date)` — per-version paths.
- `SCORE_WEIGHTS` — feature weights for the score formula (see `documentation/scoring.md`).
- `SCORE_COLORS` — RdYlGn palette `{int 1..10: (bg_hex, text_hex)}` for score badges.
- `metrics()` — feature extraction; add a feature here and in `SCORE_WEIGHTS` together.
- `score()`, `int_score()`, `score_badge_style()` — score computation and presentation helpers.
- `expand_includes()` — recursively expands `{% include %}` directives (depth-limited to 4) before metrics are collected.
- `is_single_language_expected()` — fnmatch check against `single_language_patterns`.
- `today_iso()` — `YYYY-MM-DD` stamp used for `generated_at` and `history/<date>/`.

### History

Each run of `./analyze.py` reads `docs/meta.json`. If its `generated_at` differs from today, the entire current `docs/` snapshot (everything except `history/` and `index.html`) is copied into `docs/history/<old_generated_at>/`. The fresh run then overwrites `docs/<v>/...`, `docs/summary.*`, and `docs/index.html`, and rewrites `docs/meta.json`. Multiple runs the same day overwrite the same history slot. Logic lives in `scripts/archive.py:archive_previous`.

### `cache/` is fully derived

Everything under `cache/` is gitignored. The repository is reproducible from `./download.py && ./analyze.py`. Do not check anything in under `cache/`.

### Idempotency

- `fetch.py` skips already-downloaded versions unless `--refresh` (which wipes `cache/<v>/docs/` and re-fetches).
- `compare.py` and `report.py` always overwrite their outputs.
- `archive.py` is a no-op when `meta.json` is missing or its date already matches today.
- No state outside `cache/<v>/`, `docs/`, and `config.json`.

### Error conventions

User-facing failures (missing version, missing docs) use `raise SystemExit("...")` with a Russian message. Internal bugs use regular exceptions. All CLIs emit `[stage] <version>: ...` lines so `analyze.py` logs are greppable.

## Further reading

Project documentation under `documentation/` (in Russian):
- `architecture.md` — data flow, directory layout, config schema.
- `scoring.md` — the score formula, weights, scope and limitations.
- `howto.md` — common recipes (add version, change palette, refresh, publish report, etc.).
- `modules.md` — function-level reference for each script.
