# Smoke Test Checklist

Короткая проверка нужна после изменений в `scripts/generate_cards.py`, README, CSV-шаблонах, scoring или output-форматах.

Smoke tests ничего не публикуют, не рендерят, не открывают соцсети, не используют API, логины или токены. Они только запускают локальный генератор на уже лежащих в проекте CSV.

## Быстрый запуск

```powershell
cd D:\Projects\Others\NeuroPravo_Shorts_Signal_Automation
python .\scripts\run_smoke_tests.py
```

По умолчанию runner создает временные папки в `output\_smoke_tests\`, проверяет файлы и удаляет эту временную папку после успешного завершения.

Если нужно вручную посмотреть outputs:

```powershell
python .\scripts\run_smoke_tests.py --keep-output
```

## Что проверять в normal mode

Normal mode нужен для CSV, где есть нормальные даты публикации и engagement-метрики: views, likes, comments.

Команды, которые smoke runner прогоняет в `normal`:

```powershell
python .\scripts\generate_cards.py --input data\input_videos.csv --out output\_smoke_tests\main_input --min-score 70 --metrics-mode normal
python .\scripts\generate_cards.py --input data\demos\youtube_shorts_demo.csv --out output\_smoke_tests\youtube_demo --min-score 70 --metrics-mode normal
python .\scripts\generate_cards.py --input data\demos\tiktok_apify_demo.csv --out output\_smoke_tests\tiktok_demo --min-score 70 --metrics-mode normal
python .\scripts\generate_cards.py --input data\demos\mixed_manual_import_demo.csv --out output\_smoke_tests\mixed_demo --min-score 70 --metrics-mode normal
```

Expected counts примерно:

| CSV | mode | expected |
|---|---|---|
| `data\input_videos.csv` | normal | valid rows около 4, selected больше 0 |
| `data\demos\youtube_shorts_demo.csv` | normal | valid rows около 3, selected больше 0 |
| `data\demos\tiktok_apify_demo.csv` | normal | valid rows около 3, selected больше 0 |
| `data\demos\mixed_manual_import_demo.csv` | normal | valid rows около 4, selected больше 0 |

## Что проверять в public_search mode

Public search mode нужен для открытой выдачи, где обычно есть views, но likes/comments/date неполные или approximate.

Команда:

```powershell
python .\scripts\generate_cards.py --input data\manual_batches\batch_2026-07-12.csv --out output\_smoke_tests\first_public_batch --min-score 55 --metrics-mode public_search
```

Expected counts примерно:

| CSV | mode | expected |
|---|---|---|
| `data\manual_batches\batch_2026-07-12.csv` | public_search | valid rows около 24, selected больше 0; текущая калибровка дает около 13 |

## Какие outputs должны появиться

Для каждого прогона runner проверяет:

- `scenario_cards.md`;
- `scenario_cards.csv`;
- `scenario_cards.json`;
- `batch_summary.md`;
- `validation_report.csv`.

Также проверяется, что JSON читается, CSV содержит строки, validation issues равны 0, а для public_search selected_count больше 0.

## Когда запускать

Запускать перед commit, если менялись:

- `scripts/generate_cards.py`;
- scoring или metrics mode;
- CSV-валидация;
- output Markdown/CSV/JSON;
- README-команды запуска;
- demo CSV или manual batch шаблоны.
