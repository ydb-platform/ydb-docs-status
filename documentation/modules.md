# Справочник модулей

Точки входа на верхнем уровне (`download.py`, `analyze.py`) —
тонкие orchestrator'ы. Вся логика — в `scripts/`. `lib.py` — общий
модуль, остальные импортируют его.

## Точки входа (верхний уровень)

### `download.py`

CLI: `./download.py [<version>...] [--refresh]`.

Делает: добавляет `scripts/` в `sys.path`, читает `config.json`,
для каждой запрошенной версии (или всех) зовёт
`fetch.fetch(v, refresh=...)`. Скачанное оказывается в
`cache/<v>/docs/`.

### `analyze.py`

CLI: `./analyze.py [<version>...]`.

Делает: вычисляет сегодняшнюю дату → `archive.archive_previous(today)`
→ для каждой версии зовёт `compare.compare(v)` и
`report.render(v, generated_at=today)`; в конце безусловно
`summary.render(generated_at=today)`, `index.render_landing(today, ...)`,
`index.render_history_index(...)` и запись `docs/meta.json` с сегодняшней
датой. Сеть не нужна — все данные читаются из `cache/<v>/docs/`. Если
для какой-то версии docs ещё не скачаны, `compare` упадёт с понятным
сообщением: надо запустить `./download.py <v>` сначала.

## `scripts/lib.py`

### Пути и конфиг

| Функция/константа | Назначение |
| --- | --- |
| `PROJECT_ROOT` | Корень проекта, вычисленный от `__file__`. |
| `CACHE_ROOT` | `cache/` — корень скачанных docs (gitignored). |
| `SITE_ROOT` | `docs/` — корень GH Pages сайта (коммитится). |
| `HISTORY_ROOT` | `docs/history/` — архив прошлых снимков. |
| `load_config()` | Читает `config.json`. |
| `cache_version_dir(v)` | `cache/<v>/`. |
| `site_version_dir(v)` | `docs/<v>/` — актуальный отчёт по версии. |
| `history_dir(date)` | `docs/history/<date>/`. |
| `docs_root(v)` | `cache/<v>/docs/` — поддерево `ydb/docs` версии. |
| `lang_root(v, lang, cfg)` | Корень языка внутри `docs/` (например, `.../ru/core`). |
| `require_version(v, cfg)` | Бросает `SystemExit` с понятной ошибкой, если версия не описана. |
| `today_iso()` | `YYYY-MM-DD` для `generated_at` и имён снимков. |

### Сбор страниц

`collect_pages(lang_root_path, exclude_dirs) -> list[Path]` — обходит
дерево, возвращает относительные пути к `.md`, пропуская файлы, чей
путь содержит любую из `exclude_dirs` как сегмент.

### Одноязычные страницы

`is_single_language_expected(rel_path, patterns) -> bool` — True, если
относительный путь матчит хоть один из `patterns`. Используются
fnmatch-глобы (`*` матчит и `/`, так что `public-materials/*` ловит
любую глубину). См. [scoring.md](scoring.md#страницы-вне-оценки) и
[howto.md](howto.md#одноязычные-страницы).

### Раскрытие includes

`expand_includes(text, base_dir, docs_dir, depth=0) -> str` рекурсивно
раскрывает `{% include ... %}`:

- `{% include path %}` — путь относительно `base_dir`;
- `{% include [title](path) %}` — то же самое;
- путь, начинающийся с `/`, разрешается относительно `docs_dir`.

Глубина ограничена 4 уровнями. Ненайденные включения дают пустую
строку (не падают).

### Метрики

`metrics(text) -> PageMetrics` — структурные характеристики:
`lines`, `headings_total`, `h1`, `h2`, `h3`, `code_blocks`, `links`,
`images`, `chars`, `words`.

`PageMetrics.as_dict()` — сериализация для `results.json`.

### Оценка

`score(ru: PageMetrics|None, en: PageMetrics|None) -> float` — 1..10.
Веса берутся из `SCORE_WEIGHTS`. Подробнее — [scoring.md](scoring.md).

### URL

`page_to_url(lang, rel_path, url_version, url_base=...)` — публичный
URL страницы. `index.md` отбрасывается; `url_version=None` убирает
`?version=`.

### Оценка и палитра (для отчётов)

`SCORE_COLORS: dict[int, tuple[str, str]]` — RdYlGn палитра 1..10,
формат `{балл: (фон_hex, цвет_текста_hex)}`. Используется обоими
скриптами рендера (`report.py` и `summary.py`).

`int_score(result_dict) -> int` — округляет `result["score"]` до
целого 1..10; страницы, где `ru_exists` или `en_exists` равно False,
всегда дают 1.

`score_badge_style(score_value: int | float) -> str` — возвращает
inline-CSS `background:..;color:..;` для бейджа. Принимает float
(сводка использует средние) и округляет под цвет.

## `scripts/fetch.py`

CLI: `./scripts/fetch.py <version> [--refresh]`.

Публичная функция: `fetch(version: str, *, refresh: bool=False) -> Path`.

Делает sparse-checkout `sparse_paths` из ветки `versions[version].ref`
во временную папку, затем переносит `ydb/docs` в `cache/<v>/docs/`.

## `scripts/compare.py`

CLI: `./scripts/compare.py <version>`.

Публичная функция: `compare(version: str) -> Path` (возвращает путь к
`results.json`).

Парит файлы по относительному пути от `lang_root`. Объединение
множеств ru/en гарантирует, что страницы, существующие только с одной
стороны, попадают в отчёт с пометкой. Результат — `docs/<v>/results.json`.

## `scripts/report.py`

CLI: `./scripts/report.py <version>`.

Публичная функция: `render(version: str, *, generated_at: str | None = None)
-> tuple[Path, Path]` — возвращает пути к `report.txt` и `report.html`.
Если `generated_at` не задана, берётся `lib.today_iso()`. Дата попадает
в шапку обоих файлов («Сгенерировано: …»).

Шаги:

1. `_build_rows(results, url_version, url_base)` — общая для обоих
   форматов структура; формирует ru/en URL'ы и разделяет строки на
   основные и «ожидаемо одноязычные» (пара с `single_language_expected`
   только на одной стороне).
2. `_render_text(...)` — компактный текст с двумя колонками (оценка +
   ru URL), гистограммой и разрезом по разделам.
3. `_render_html(...)` — self-contained HTML; цветовые бейджи берутся
   из `lib.SCORE_COLORS` (палитра RdYlGn). CSS встроен в файл,
   внешних ресурсов нет.

Изменить палитру — `lib.SCORE_COLORS`; стилизацию HTML — `_build_css`
в `report.py` (или `summary.py` для сводки).

## `scripts/summary.py`

CLI: `./scripts/summary.py` (без аргументов).

Публичная функция: `render(*, generated_at: str | None = None) ->
tuple[Path, Path]` — возвращает пути к `docs/summary.txt` и
`docs/summary.html`. Если `generated_at` не задана, берётся
`lib.today_iso()`.

Шаги:

1. `_collect(config)` — для каждой версии из конфига пробует прочитать
   `docs/<v>/results.json`. Если файл отсутствует, версия пропускается
   с предупреждением (не падаем).
2. `_per_version_stats(results)` — приватный редьюсер: считает
   `total`, `avg`, `hist`, `by_section` (`{section: (avg, n)}`),
   `single_lang`. Логика согласована с `report.py` (страницы
   `single_language_expected` без перевода исключаются).
3. `_render_text(...)` — таблица итогов, матрица распределения
   (версия × балл), таблица разделов (раздел × версия).
4. `_render_html(...)` — то же в HTML с цветными ячейками; имена
   версий — ссылки на per-version `report.html` (относительный путь
   `<version>/report.html`). В шапке — «Сгенерировано: …».

CSS встроен. Палитра — `lib.SCORE_COLORS`, поэтому правка цветов
в одном месте отражается и в per-version, и в сводном отчёте.

## `scripts/archive.py`

CLI: `./scripts/archive.py [<today>]`.

Публичная функция:
`archive_previous(today: str | None = None) -> str | None`.

Алгоритм:

1. Если `docs/meta.json` нет — `None` (нечего архивировать).
2. Если `meta["generated_at"] == today` — `None` (повторный прогон
   в тот же день; актуальная папка просто перезапишется).
3. Иначе пересоздать `docs/history/<old_date>/` и скопировать туда
   всё содержимое `docs/` за исключением `history/` и `index.html`.

Возвращает дату старого снимка. `index.html` не входит в архив, потому
что у каждого снимка своя сводка `summary.html` как самостоятельная
точка входа, а навигация по архиву строится отдельно
(`docs/history/index.html`).

## `scripts/index.py`

CLI: `./scripts/index.py [<generated_at>]` (по умолчанию — сегодня).

Публичные функции:

- `history_dates() -> list[str]` — имена подпапок `docs/history/` в
  обратном хронологическом порядке (имена `YYYY-MM-DD` отсортированы
  лексикографически = хронологически).
- `render_landing(generated_at: str | None = None, dates: list[str] |
  None = None) -> Path` — рисует `docs/index.html`: заголовок, дата
  последнего прогона, ссылка на `summary.html`, до 5 последних дат
  истории inline, ссылка на полный индекс.
- `render_history_index(dates: list[str] | None = None) -> Path` —
  рисует `docs/history/index.html`: список ссылок на
  `<date>/summary.html`.

CSS встроен в `_css()`, файлы self-contained.

## Конвенции

- Все CLI выводят строки вида `[stage] <version>: ...` — удобно для
  grep в логе `analyze.py`.
- Падения — `raise SystemExit(...)` с текстом на русском (как
  пользовательское сообщение); внутренние баги — обычные исключения.
- Никаких сторонних зависимостей. Только стандартная библиотека Python
  и `git`.
- Импорт между скриптами: `download.py` и `analyze.py` добавляют
  `scripts/` в `sys.path` и делают `import lib`, `import fetch as fetch_mod`
  и т. п. Внутри `scripts/*.py` модули импортируют друг друга по короткому
  имени (`import lib`).
