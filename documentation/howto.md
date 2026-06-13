# Recipes

## Full run from scratch

```bash
./download.py     # network: sparse-checkout every version into cache/
./analyze.py      # local: archive + metrics + reports + summary + landing
```

## Add a new YDB version

1. Find the branch name in `ydb-platform/ydb` (e.g. `stable-26-2`).
2. Add an entry to `config.json`:
   ```json
   "26.2": {"ref": "stable-26-2", "url_version": "v26.2"}
   ```
3. Run:
   ```bash
   ./download.py 26.2
   ./analyze.py
   ```

No code change needed. `./analyze.py` without arguments always rebuilds
the summary and landing for every available version.

## Refresh an already-added version

`stable-*` branches occasionally get patches, and `main` moves all the
time:

```bash
./download.py --refresh main
./download.py --refresh 26.1
./analyze.py
```

Without `--refresh`, `download.py` skips already-fetched folders.

## Run only the comparison (no re-fetch)

Once `cache/<v>/docs/` is in place:

```bash
./analyze.py 25.3
```

Useful when you tweak metrics/weights and want to recompute without
hitting the network.

## Open an HTML report in a browser

`./analyze.py` always writes `report.txt` next to `report.html`.

```bash
open docs/index.html             # landing with navigation
open docs/summary.html           # summary — the practical entry point
open docs/main/report.html       # per-version detail
xdg-open docs/main/report.html   # Linux
```

In HTML you get a colored score badge (red `1` to green `10`),
clickable RU and EN links, separate blocks for statistics and for
"expected single-language pages". The report header includes a
"Generated: YYYY-MM-DD" line.

## Publish an updated report

Everything is under `docs/`, and that folder is committed. GitHub
Pages serves it automatically.

```bash
./download.py --refresh main
./analyze.py
git add docs
git status                   # see what changed
git commit -m "docs: snapshot $(date +%Y-%m-%d)"
git push
```

Within a minute or two the site updates. The URL is in Settings → Pages.

To refresh just one version without rebuilding everything:

```bash
./analyze.py 25.3            # rebuilds 25.3, the summary, and the landing
git add docs/25.3 docs/summary.* docs/index.html docs/meta.json
git commit -m "docs(25.3): refresh $(date +%Y-%m-%d)"
git push
```

## Open a past snapshot

Snapshots live under `docs/history/<YYYY-MM-DD>/` (see
[architecture.md → Snapshot archive](architecture.md#snapshot-archive)).

```bash
open docs/history/index.html                          # full list
open docs/history/2026-06-01/summary.html             # specific snapshot
```

To compare two summaries with a plain diff:

```bash
diff docs/history/2026-06-01/summary.txt docs/summary.txt
```

## Rebuild only the summary

```bash
./scripts/summary.py
```

Useful when you've hand-edited `results.json` or changed the palette.
`./analyze.py` calls `summary.py` at the end automatically, so after a
normal run `docs/summary.{txt,html}` are already current.

The summary contains:

- the totals table (Pages / Avg / Score=1 / Score=10 / One-lang);
- the score-distribution matrix (version × bucket);
- the average-score table by section (section × version) — useful for
  spotting trends.

Versions without a `results.json` are skipped with a warning — handy
when a new version is in the config but `./analyze.py` hasn't been run
for it yet.

## Rebuild only the landing page

```bash
./scripts/index.py
```

Re-reads the snapshot list from `docs/history/` and rewrites
`docs/index.html` + `docs/history/index.html`. The run date defaults
to today (override via the CLI argument; see `--help`). `./analyze.py`
calls this step automatically.

## Force the archive to repack

If for some reason you want to re-archive the current state by hand:

```bash
echo '{"generated_at": "2026-01-01"}' > docs/meta.json
./analyze.py
```

`archive.py` notices the date mismatch and copies the current snapshot
into `docs/history/2026-01-01/`. After the run, `docs/meta.json` is
rewritten with today's date.

## Change the score palette

Edit the `SCORE_COLORS` dict in `scripts/lib.py`:
`{score: (background_hex, text_hex)}`. Then run `./analyze.py` (or
just `./scripts/report.py <v>` + `./scripts/summary.py`) — no download
needed. The palette is shared between per-version and summary
reports.

## See only the problematic pages

```bash
grep -E '^\s+([1-7])\s' docs/25.3/report.txt
```

`report.txt` is sorted by score ascending, so problems come first.

## Compare distributions across versions

```bash
for v in 25.3 25.4 26.1 main; do
  echo "=== $v ==="
  grep -A20 'Score distribution' docs/$v/report.txt
done
```

## Single-language pages

If you have pages that exist in only one language **by design** (e.g.
talk announcements written specifically in Russian or English under
`public-materials/`), you can exclude them from the main report so they
don't count as "missing translation".

In `config.json`:

```json
"single_language_patterns": [
  "public-materials/*",
  "blog/podcasts-ru/*"
]
```

A pattern is an fnmatch glob over the **relative path** of the page
(relative to `ru/core` or `en/core`). `*` matches any character,
including `/`, so `public-materials/*` covers any depth under that
folder.

What happens:

- a page matching the pattern that exists in only one language is
  removed from the main table and the histogram;
- such pages appear in a separate section at the end of `report.txt`
  with an `[RU-only]` or `[EN-only]` tag;
- if the same page later appears in both languages, it is scored
  normally.

See the scoring impact in [scoring.md](scoring.md#pages-outside-scoring).

## Change the list of excluded folders

In `config.json`:

```json
"exclude_dirs": ["_includes", "_assets", "_examples"]
```

This affects only the list of **pages** considered as comparison units.
Include expansion keeps working (see [architecture.md](architecture.md)).

## Change the scoring methodology

Edit the weights or add a feature in `scripts/lib.py`: `SCORE_WEIGHTS`
and `metrics`. Details in [scoring.md](scoring.md).

## Clear the local cache for a version

```bash
rm -rf cache/25.3
```

The next `./download.py 25.3` re-fetches it. `docs/25.3/` stays as it
was — it will be regenerated by the next `./analyze.py 25.3`.

## Commit the project to git from scratch

`.gitignore` already excludes `cache/`, `__pycache__/`, `.DS_Store`,
`.claude/settings.local.json`. `docs/` is committed. Safe to run:

```bash
git init
git add -A
git commit -m "Initial commit"
```

Anyone cloning the repo runs `./download.py && ./analyze.py` and sees
exactly the same reports that ship in `docs/`.
