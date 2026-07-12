# NeuroPravo Shorts Signal Automation

Локальный import-first инструмент для поиска и разбора залетевших коротких видео под сценарии НейроПраво.

Инструмент ничего не публикует, не рендерит, не загружает в аккаунты и не подключает внешние API. На текущем этапе он берет готовый CSV из ручного импорта, Apify, ViewStats или другой выгрузки, валидирует строки, считает score и делает карточки сценариев.

## Быстрый запуск

1. Положите CSV в:

```text
D:\Projects\Others\NeuroPravo_Shorts_Signal_Automation\data\input_videos.csv
```

2. Запустите:

```powershell
cd D:\Projects\Others\NeuroPravo_Shorts_Signal_Automation
python .\scripts\generate_cards.py --input data\input_videos.csv --out output
```

3. Результаты будут здесь:

```text
output\scenario_cards.md
output\scenario_cards.csv
output\scenario_cards.json
output\validation_report.csv
```

## Порог отбора и режим метрик

Есть два рабочих режима.

`normal` используйте для полных импортов: Apify, ViewStats, ручная таблица или CSV, где есть нормальная дата публикации, просмотры, лайки и комментарии. Рекомендуемый порог:

```powershell
python .\scripts\generate_cards.py --input data\input_videos.csv --out output --min-score 70 --metrics-mode normal
```

`public_search` используйте для открытой поисковой выдачи, где обычно видны ссылка и просмотры, но лайки, комментарии и точная дата не видны. Рекомендуемый порог:

```powershell
python .\scripts\generate_cards.py --input data\manual_batches\batch_2026-07-12.csv --out output\first_real_batch_2026-07-12_public_search --min-score 55 --metrics-mode public_search
```

Если режим не указать, инструмент попробует определить его автоматически. Для важных партий лучше задавать режим явно.

В `public_search` нулевые likes/comments не считаются плохой реакцией, если в `notes` указано `unknown`, `visible_on_page` или `approximate`. Такой shortlist редакторский: перед производством нужно вручную открыть выбранные ролики и проверить содержание.

## Smoke tests

Короткая regression-проверка генератора:

```powershell
python .\scripts\run_smoke_tests.py
```

Checklist: `docs\Smoke_Test_Checklist.md`.
## CSV-шаблон

Шаблон лежит здесь:

```text
data\templates\import_template.csv
```

Обязательные колонки:

```text
source_url
platform
published_at
author
title_or_caption
views
likes
comments
shares
saves
duration_sec
topic_hint
notes
```

Разрешенные `platform`:

```text
YouTube Shorts
TikTok
Instagram Reels
VK Clips
Dzen
ViewStats
Apify
Manual
```

Дата: `YYYY-MM-DD`. Инструмент отсекает строки старше 30 дней и будущие даты.

Числа можно писать обычным числом, пустые значения считаются нулем. Поддерживаются короткие формы вроде `12k`, `1.5m`, `12к`, `1.5м`.


## Ручные редакторские партии

Для первой реальной партии 20-50 роликов используйте папку:

```text
data\manual_batches\
```

Шаблон партии:

```text
data\manual_batches\batch_template_YYYY-MM-DD.csv
```

Пример с demo-данными:

```text
data\manual_batches\sample_manual_batch.csv
```

Запуск sample batch:

```powershell
python .\scripts\generate_cards.py --input data\manual_batches\sample_manual_batch.csv --out output\sample_manual_batch --min-score 70
```

Главный файл для быстрого просмотра теперь:

```text
output\...\batch_summary.md
```

В нем видно качество партии, платформы, темы, причины отсева, топ-10 по `final_score`, топ-5 по `neuropravo_fit_score` и блок `Смотреть первыми`.

Подробная инструкция:

```text
docs\Manual_Import_Workflow.md
```

## Первый реальный прогон

Перед подключением API нужно провести один настоящий ручной прогон. Он покажет, какие темы реально дают материал, какие поля удобно заполнять, и что в scoring надо поправить.

Пошаговая инструкция:

```text
docs\First_Real_Batch_Collection_Guide.md
```

План на 50 мест:

```text
data\manual_batches\first_real_batch_plan_2026-07-12.md
```

Набор поисковых запросов:

```text
config\search_queries_ru.json
```

Рабочий маршрут:

1. Открыть guide.
2. По таблице-плану найти 20-50 роликов вручную.
3. Заполнить ссылку, просмотры, лайки, комментарии, заметку и решение `брать/не брать`.
4. Лучшие строки перенести в CSV `data\manual_batches\batch_2026-07-12.csv` по шаблону.
5. Запустить:

```powershell
python .\scripts\generate_cards.py --input data\manual_batches\batch_2026-07-12.csv --out output\first_real_batch_2026-07-12 --min-score 70
```

Сначала читать:

```text
output\first_real_batch_2026-07-12\batch_summary.md
```

Потом карточки:

```text
output\first_real_batch_2026-07-12\scenario_cards.md
```

На этом этапе не подключайте scraping, API, логины, токены и платные сервисы.
## Demo CSV

Проверочные файлы:

```text
data\demos\youtube_shorts_demo.csv
data\demos\tiktok_apify_demo.csv
data\demos\mixed_manual_import_demo.csv
```

Запуск YouTube Shorts demo:

```powershell
python .\scripts\generate_cards.py --input data\demos\youtube_shorts_demo.csv --out output\youtube_demo
```

Запуск TikTok/Apify demo:

```powershell
python .\scripts\generate_cards.py --input data\demos\tiktok_apify_demo.csv --out output\tiktok_demo
```

Запуск mixed manual demo:

```powershell
python .\scripts\generate_cards.py --input data\demos\mixed_manual_import_demo.csv --out output\mixed_demo
```

## Scoring

Для каждого ролика считаются:

- `raw_score`: просмотры + комментарии x 30 + лайки x 3 + репосты x 30 + сохранения x 40;
- `engagement_score`: вовлеченность относительно просмотров;
- `recency_score`: свежесть внутри 30-дневного окна;
- `neuropravo_fit_score`: совпадение с темами, конфликтами и legal/biz-сигналами;
- `final_score`: итоговый score 0-100.

Каждая строка получает `selection_reason` и, если отсеяна, `rejection_reasons`.

## Формат сценариев

Сценарии пишутся компактно: 6 плотных абзацев, без лесенки по одному предложению в строке.

Правила безопасности:

- не копировать чужой текст;
- не обещать юридический результат;
- не писать `100% выиграете`;
- не давать индивидуальную юридическую консультацию;
- сохранять ручной финальный выбор Александра.

## Что можно подключить позже

Только отдельной командой Александра:

- YouTube Data API;
- Apify;
- Google Sheets / Airtable;
- LLM-вызов вместо локальной эвристики.

Секреты, токены, cookies и ключи не хранить в GitHub, README, CSV или памяти проекта.





