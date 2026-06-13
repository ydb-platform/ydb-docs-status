# ydb_ru_eng_sync

Сравнение русской и английской версий документации [YDB](https://ydb.tech)
по нескольким версиям продукта. Для каждой страницы вычисляется оценка
1..10, где 1 — страница отсутствует в одном из языков или сильно
расходится, 10 — версии практически идентичны.

Готовые отчёты публикуются на GitHub Pages (см. ниже).

## Зависимости

- Python 3.10+
- `git` 2.25+ (нужен `sparse-checkout` и `--filter=blob:none`)
- Доступ в интернет до `github.com`

## Быстрый старт

```bash
./download.py     # скачать docs всех версий из ydb-platform/ydb в cache/
./analyze.py      # сравнить ru/en, собрать отчёты в docs/
```

Открыть результат локально:

```bash
open docs/index.html             # лендинг: ссылки на сводку и историю
open docs/summary.html           # удобная точка входа: все версии
open docs/main/report.html       # детально по конкретной версии
```

Если меняешь методологию (веса, паттерны), сеть не нужна:

```bash
./analyze.py      # пересчёт по уже скачанным docs (cache/)
```

## Что лежит в репозитории

```
ydb_ru_eng_sync/
├── README.md
├── CLAUDE.md
├── config.json                 # реестр версий и общие настройки
├── download.py                 # entry point: скачать docs в cache/
├── analyze.py                  # entry point: archive → compare → report → summary → index
├── scripts/                    # реализация (fetch, compare, report, summary, archive, index, lib)
├── documentation/              # внутренние md по самому проекту (для разработчиков)
├── cache/                      # (gitignored) скачанные docs YDB
└── docs/                       # КОММИТИТСЯ — корень GH Pages сайта
    ├── index.html              # лендинг
    ├── summary.{html,txt}      # актуальная сводка
    ├── <v>/                    # актуальный отчёт по версии
    └── history/<YYYY-MM-DD>/   # архив прошлых снимков
```

Два «docs» в корне репозитория — это не дубль:

| Каталог | Что внутри |
| --- | --- |
| `docs/` | Сгенерированный HTML-сайт, корень GitHub Pages. **Коммитится.** |
| `documentation/` | Внутренние md по проекту (архитектура, рецепты, справочник модулей) — читаем глазами, не публикуем. |

Тяжёлые скачанные `cache/<v>/docs/` (~100 МБ × N версий) исключены
`.gitignore` и восстанавливаются командой `./download.py`.

## История отчётов

В `docs/meta.json` хранится дата последнего прогона. На каждом запуске
`./analyze.py`:

1. Если дата в `meta.json` отличается от сегодняшней, текущий снимок
   `docs/` (без `history/` и `index.html`) копируется в
   `docs/history/<old_date>/`.
2. Регенерируются `docs/<v>/...`, `docs/summary.*`, `docs/index.html`.
3. `docs/meta.json` обновляется новой датой.

Несколько прогонов в один день перезаписывают папку текущего дня — в
истории сохраняется последний снимок дня. Внутри каждого отчёта
(`summary.html`, `<v>/report.html`) есть строка «Сгенерировано: …».

## Командный workflow

Любой член команды:

```bash
git pull
./download.py            # подкачать обновления (главное — main и stable-*)
./analyze.py             # обновить отчёты
git add docs             # docs/ коммитится; cache/ — нет
git commit -m "docs: snapshot $(date +%Y-%m-%d)"
git push
```

После пуша GitHub Pages автоматически обновляет сайт (см. ниже).

Чтобы посмотреть, что именно изменилось в отчётах:

```bash
git diff --stat docs/
git diff docs/summary.txt    # txt-варианты удобно ревьюить в git diff
```

## GitHub Pages

Одноразовая настройка для владельца репозитория:

1. **Settings → Pages**.
2. **Source**: *Deploy from a branch*.
3. **Branch**: `main`, **Folder**: `/docs`.
4. Сохранить.

Никаких GitHub Actions не нужно — Pages раздаёт содержимое `docs/`
напрямую из ветки `main`. URL сайта появится в той же странице
настроек.

## Добавить новую версию YDB

1. Открыть [`config.json`](config.json), добавить запись в `"versions"`:
   ```json
   "26.2": {"ref": "stable-26-2", "url_version": "v26.2"}
   ```
2. Запустить:
   ```bash
   ./download.py 26.2
   ./analyze.py
   ```

## Тонкая настройка

- `./download.py <v>...` / `./analyze.py <v>...` — работа с подмножеством версий.
- `./download.py --refresh <v>` — принудительная перекачка (нужно при сдвиге `main` или хотфиксе в `stable-*`).
- Отдельные шаги можно вызывать напрямую через `scripts/fetch.py`,
  `scripts/compare.py`, `scripts/report.py`, `scripts/summary.py`,
  `scripts/archive.py`, `scripts/index.py` — у каждого есть `--help`.

## Документация по проекту

- [documentation/architecture.md](documentation/architecture.md) — устройство системы, поток данных.
- [documentation/scoring.md](documentation/scoring.md) — методология оценки, веса, ограничения.
- [documentation/howto.md](documentation/howto.md) — типовые рецепты.
- [documentation/modules.md](documentation/modules.md) — справочник функций и модулей.
