# Scoring methodology

## Scale

| Score | Meaning                                                              |
| ----- | -------------------------------------------------------------------- |
| 1     | The page is missing on one side, or the content differs sharply.     |
| 5     | Structurally similar but with noticeable differences in length, sections, or examples. |
| 8–9   | Close in structure and content, minor mismatches.                    |
| 10    | Structurally identical across all metrics.                           |

## What is measured

The score is a structural proxy for semantic similarity. For each
page (after stripping the YAML frontmatter and expanding
`{% include ... %}` directives) we collect:

| Feature          | What it counts             |
| ---------------- | -------------------------- |
| `lines`          | Line count (diagnostic).   |
| `headings_total` | All headings `#`..`######`. |
| `h1`, `h2`, `h3` | Broken out for debugging.  |
| `code_blocks`    | Number of triple-backtick fence blocks. |
| `links`          | Markdown links `](...`.    |
| `images`         | Images `![...]`.           |
| `chars`          | Length excluding whitespace. |
| `words`          | "Word" count (`\S+`).      |

`lines`, `h1`, `h2`, `h3` are kept in `results.json` for inspection
but don't feed into the final score (they would double-count with
`headings_total`).

## Formula

```
score = 1 + 9 * Σ weight_i * ratio_i
```

with `ratio(a, b) = min(a,b) / max(a,b)` (or 1 if both are zero) and
`Σ weight_i = 1`. Current weights:

| Feature          | Weight |
| ---------------- | --- |
| `headings_total` | 0.25 |
| `words`          | 0.20 |
| `chars`          | 0.10 |
| `code_blocks`    | 0.20 |
| `links`          | 0.15 |
| `images`         | 0.10 |

If a page is missing on one side, `score` is set to 1.0 directly
without computation.

## Pages outside scoring

Some pages exist on only one language **by design**: for example,
materials under `public-materials/` are announcements of talks given
in a specific language and aren't translated. Such pages shouldn't
drag the bottom of the distribution as "missing translations".

Mechanism: `config.json` has a `single_language_patterns` field — a
list of fnmatch globs over relative page paths. If a page path
matches any pattern **and** the page exists in only one language,
then it:

- gets the `single_language_expected: true` flag in `results.json`;
- is excluded from the main `report.txt` table and the histogram;
- shows up in a dedicated section at the end of the report with a
  side marker (`[RU-only]` / `[EN-only]`).

If the same page later appears in both languages, it is scored
normally and joins the main table.

How to add or edit the patterns — [howto.md](howto.md#single-language-pages).

## What the score is NOT

- This is **not** real semantic comparison. Two pages can be
  structurally identical but use different wording or even state
  different facts, and still score 10.
- Localized links (e.g. wiki en/ru) may slightly lower the `links`
  ratio even when the meaning is the same.
- The weights were chosen empirically on v25.3/concepts; if average
  scores drift significantly, revisit them in `lib.SCORE_WEIGHTS`.

## Reading `report.txt`

1. Start with the 1s — missing pages.
2. 6–8 — structurally different, worth a manual look.
3. 9–10 — structurally close, but wording may still differ.
4. The end of the report has the histogram and the by-section
   breakdown (average score by the first path segment).

## Changing the methodology

- Weights and feature set — `scripts/lib.py`: the `SCORE_WEIGHTS`
  constant and the `metrics` function.
- Rounding in the report — `scripts/report.py`: `_to_int_score`.
- After changing the formula, lock the new baseline (the v25.3 score
  distribution) into [howto.md](howto.md) and the commit message.
