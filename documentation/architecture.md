# Архитектура

## Цель

Получить количественную картину расхождений между русской и английской
версиями документации YDB для нескольких версий продукта. Источник
истины — markdown-файлы в [`ydb-platform/ydb`](https://github.com/ydb-platform/ydb)
в подпапке `ydb/docs/`. Готовые отчёты публикуются на GitHub Pages
сайтом из каталога `docs/`.

## Дерево проекта

```
ydb_ru_eng_sync/
├── README.md
├── CLAUDE.md
├── .gitignore                  # исключает cache/
├── config.json                 # реестр версий и общие настройки
├── download.py                 # ВЕРХНИЙ УРОВЕНЬ: скачать docs всех версий в cache/
├── analyze.py                  # ВЕРХНИЙ УРОВЕНЬ: archive + compare + report + summary + index
├── scripts/                    # реализация (импортируется entry-point'ами)
│   ├── lib.py                  # общие функции и константы (пути, метрики, палитра)
│   ├── fetch.py                # sparse-checkout ydb/docs для одной версии в cache/
│   ├── compare.py              # парные метрики + score → docs/<v>/results.json
│   ├── report.py               # results.json → docs/<v>/report.{txt,html}
│   ├── summary.py              # кросс-версионная сводка → docs/summary.{txt,html}
│   ├── archive.py              # снимок текущего docs/ → docs/history/<old_date>/
│   └── index.py                # лендинг docs/index.html + docs/history/index.html
├── documentation/              # внутренние md по САМОМУ проекту
├── cache/                      # (gitignored) скачанные docs YDB по версиям
│   └── <version>/
│       └── docs/               # содержимое ydb/docs из ветки версии
│           ├── _includes/      # общие партиалы (важны для compare)
│           ├── _assets/
│           ├── ru/core/...     # русские страницы
│           └── en/core/...     # английские страницы
└── docs/                       # КОММИТИТСЯ — корень GH Pages сайта
    ├── meta.json               # {"generated_at": "YYYY-MM-DD"} последнего прогона
    ├── index.html              # лендинг (точка входа сайта)
    ├── summary.{txt,html}      # актуальная кросс-версионная сводка
    ├── <version>/              # актуальный отчёт по версии
    │   ├── results.json        # машинно-читаемые попарные метрики
    │   ├── report.txt          # компактный текст (для grep/diff)
    │   └── report.html         # интерактивный отчёт для браузера
    └── history/
        ├── index.html          # список снимков (обратный хронологический)
        └── <YYYY-MM-DD>/       # снимок сайта на эту дату
            ├── meta.json
            ├── summary.{txt,html}
            └── <version>/...
```

### Два «docs» в корне — не путать

| Каталог | Назначение |
| --- | --- |
| `docs/` | Сгенерированный HTML-сайт, корень GitHub Pages. Коммитится. |
| `documentation/` | Внутренняя md-документация для разработчиков. Коммитится, но не часть публичного сайта. |

Имя `docs/` зафиксировано конвенцией GitHub Pages в режиме *Deploy from a
branch*: раздаются только корень репо и `/docs`. Переименовать без
включения Actions-workflow нельзя.

`cache/` целиком исключён из git (см. `.gitignore`): скачанные docs —
тяжёлое (≈100 МБ на версию) производное, восстанавливается командой
`./download.py`.

## Entry points

На верхнем уровне — два скрипта:

| Скрипт          | Что делает                                            |
| --------------- | ----------------------------------------------------- |
| `./download.py` | Sparse-checkout `ydb/docs` каждой версии из конфига в `cache/<v>/docs/`. Сетевая операция. |
| `./analyze.py`  | Архив прошлого снимка → для каждой версии: `compare` → `report`; в конце `summary` + `index`; пишет `docs/meta.json`. Сеть не нужна. |

Оба принимают необязательный список версий и `--help`. Реальная логика
живёт в `scripts/`, эти entry point'ы — тонкие orchestrator'ы (~30 строк),
добавляют `scripts/` в `sys.path` и зовут публичные функции модулей.

## Поток данных

```
docs/meta.json
    │
    ▼
archive.py — если generated_at ≠ сегодня, копируем
             всё docs/* (кроме history/ и index.html)
             в docs/history/<old_date>/

config.json
    │
    ▼
fetch.py  ──── git clone --sparse ─── ydb-platform/ydb
    │                                         │
    │                                         └── ydb/docs/
    ▼
cache/<v>/docs/
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
    │  ─ page_to_url для ru и en (с ?version=)
    │  ─ сортировка, гистограмма, разрез по разделам
    │  ─ выделение «ожидаемо одноязычных» в отдельную секцию
    │  ─ generated_at в шапке (txt + html)
    ▼
docs/<v>/report.txt + report.html
    │
    │  (после прохода по всем версиям)
    ▼
summary.py — читает все docs/<v>/results.json
    ▼
docs/summary.txt + summary.html (generated_at в шапке)
    │
    ▼
index.py — список дат из docs/history/, рендер лендинга
    ▼
docs/index.html + docs/history/index.html
    │
    ▼
write docs/meta.json = {"generated_at": today}
```

### HTML-отчёт

Self-contained файл (всё CSS внутри, без внешних зависимостей):

- Шапка: версия, источник, дата генерации, легенда шкалы.
- Блок статистики: распределение оценок и средняя по разделам.
- Основная таблица: оценка (цветной бейдж по палитре RdYlGn), путь
  страницы и две колонки со ссылками — RU и EN. Отсутствующая сторона
  показывается прочерком.
- Блок «ожидаемо одноязычные страницы»: компактный список со ссылкой
  на существующую версию и пометкой `RU-only` / `EN-only`.

Цветовая палитра задана в `scripts/lib.py` в константе `SCORE_COLORS`
— словарь `{балл → (фон, текст)}`. Менять — там, после правки правится
и per-version `report.html`, и `summary.html`.

### Сводный отчёт по версиям

`scripts/summary.py` агрегирует все `docs/<v>/results.json` и
формирует:

- `docs/summary.txt` — итоговая таблица, матрица распределения
  оценок (версия × балл) и таблица «средняя оценка по разделам»
  (раздел × версия), дата генерации в шапке.
- `docs/summary.html` — то же самое в интерактивном виде:
  ячейки матриц подкрашены палитрой `SCORE_COLORS`, имена версий —
  кликабельные ссылки на per-version `report.html`. Подходит как
  главная точка входа после `index.html`.

Версии, для которых ещё нет `results.json`, пропускаются с
предупреждением. `analyze.py` вызывает `summary.render()` в конце
прохода, так что сводка всегда соответствует последнему состоянию
данных на диске.

### Лендинг и индекс истории

`scripts/index.py` рисует два HTML:

- `docs/index.html` — точка входа сайта: заголовок, дата последнего
  прогона, ссылка на `summary.html`, краткий список последних дат
  истории, ссылка на полный индекс.
- `docs/history/index.html` — обратный хронологический список всех
  снимков; каждая ссылка ведёт на `<date>/summary.html`.

Оба self-contained, CSS встроен, без внешних ресурсов.

### Архив прошлых снимков

`scripts/archive.py` читает `docs/meta.json` и, если зафиксированная
там дата отличается от текущей, копирует всё содержимое `docs/` (кроме
самой `history/` и `index.html`) в `docs/history/<old_date>/`. Внутри
снимка сохраняется собственный `meta.json` и `summary.{txt,html}` —
снимок можно открывать и читать самостоятельно.

Повторный прогон того же дня — no-op для архива (новые отчёты просто
перезаписывают актуальную копию). Если нужно перерисовать архив руками,
достаточно подправить `docs/meta.json` (поставить старую дату) и
запустить `./analyze.py`.

## Конфигурация (`config.json`)

| Поле           | Назначение                                                  |
| -------------- | ----------------------------------------------------------- |
| `repo`         | URL git-репозитория YDB.                                    |
| `sparse_paths` | Список путей для `git sparse-checkout set`.                 |
| `languages`    | Соответствие языкового кода и корня внутри `ydb/docs`.       |
| `exclude_dirs` | Папки, чьё содержимое не считается отдельными страницами.    |
| `single_language_patterns` | fnmatch-глобы относительных путей страниц, которые **по дизайну** существуют только на одном языке (например, `public-materials/*`). Такие страницы не попадают в score 1 «отсутствует перевод», а выносятся в отдельную секцию отчёта. См. [howto.md](howto.md#одноязычные-страницы). |
| `url_base`     | База публичного URL документации.                           |
| `versions`     | Карта `<version> → {ref, url_version}`.                     |

Менять структуру дерева в репозитории YDB можно из конфига, не правя код.

## Что лежит в `results.json`

Массив объектов:

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

`single_language_expected: true` означает, что путь матчит один из паттернов
`single_language_patterns` (см. [howto.md](howto.md#одноязычные-страницы)).
Если такая страница существует только на одном языке — это ожидаемое
поведение, и в основной отчёт она не попадает.

`score` — float в диапазоне [1.0, 10.0]; в `report.txt` он округляется
до целого. Если страница отсутствует в одном из языков, обе метрики
могут быть `null`, а `score` гарантированно равен 1.

Дата генерации в `results.json` не дублируется: единственный источник
правды — `docs/meta.json`.

## Идемпотентность и кэширование

- `fetch.py` без `--refresh` пропускает уже скачанные версии. С
  `--refresh` папка `cache/<v>/docs/` удаляется и пересоздаётся.
- `compare.py`, `report.py`, `summary.py`, `index.py` всегда
  перезаписывают свои выходные файлы.
- `archive.py` — no-op, если `docs/meta.json` нет либо его
  `generated_at` уже равен сегодняшней дате.
- Никаких глобальных состояний за пределами `cache/`, `docs/` и
  `config.json` система не держит.
