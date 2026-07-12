# NeuroPravo Shorts Signal Automation

Локальный import-first инструмент для поиска и разбора залетевших коротких видео под сценарии НейроПраво. Текущая стратегия: viral-first, then legal-fit.

Инструмент ничего не публикует, не рендерит, не загружает в аккаунты и не подключает внешние API. На текущем этапе он берет готовый CSV из ручного импорта, Apify, ViewStats или другой выгрузки, валидирует строки, считает score и делает карточки сценариев.
## Главная цель: находить, а не разово найти

Проект строит регулярный конвейер:

```text
сбор viral-first коротких роликов -> source review -> оценка механики залета -> проверка НейроПраво -> только потом сценарий
```

Перед сценариями всегда смотрите:

```text
output\...\source_candidates_review.md
```

Этот файл показывает исходные ролики, метрики, статус `ЗАЛЕТЕВШИЙ-КАНДИДАТ` / `ПОТЕНЦИАЛЬНЫЙ-СИГНАЛ` / `НЕ БРАТЬ`, причину выбора и насколько сильно будущий сценарий должен отличаться от исходника.

Операционная модель: `docs\Signal_Discovery_Operating_Model.md`.
Viral-first стратегия: `docs\Viral_First_Discovery_Strategy.md`.
Правила сигнала: `config\viral_signal_rules.json`.
Регулярный сбор источников: `docs\Recurring_Source_Acquisition.md`.

Окно 1 отвечает за нахождение и проверку сигнала. Окно 2 получает задачу на сценарий только после source review. Не искать сначала `юрист + тема`; юридическая релевантность проверяется после viral mechanic.

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
output\source_candidates_review.md
output\discovery_manifest.md
output\batch_summary.md
output\scenario_cards.md
output\scenario_cards.csv
output\scenario_cards.json
output\validation_report.csv
```

## Регулярный source acquisition

Окно 1 обновляет не сценарии, а входные партии источников. Рабочие CSV лежат здесь:

```text
data\source_acquisition\24-72h\discovery_YYYY-MM-DD_24-72h.csv
data\source_acquisition\7d\discovery_YYYY-MM-DD_7d.csv
data\source_acquisition\30d\discovery_YYYY-MM-DD_30d.csv
```

Подробная инструкция: `docs\Recurring_Source_Acquisition.md`.

24-72h fresh scan:

```powershell
python .\scripts\generate_cards.py --input data\source_acquisition\24-72h\discovery_2026-07-12_24-72h.csv --out output\discovery_2026-07-12_24-72h --min-score 55 --metrics-mode public_search
```

7d weekly scan:

```powershell
python .\scripts\generate_cards.py --input data\source_acquisition\7d\discovery_2026-07-12_7d.csv --out output\discovery_2026-07-12_7d --min-score 55 --metrics-mode public_search
```

30d monthly scan:

```powershell
python .\scripts\generate_cards.py --input data\source_acquisition\30d\discovery_2026-07-12_30d.csv --out output\discovery_2026-07-12_30d --min-score 55 --metrics-mode public_search
```

Первым всегда открывать:

```text
output\...\discovery_manifest.md
output\...\source_candidates_review.md
```

Если `discovery_manifest.md` показывает `NEEDS-BETTER-SOURCE-BATCH`, Окно 2 не пишет сценарий. Нужно добрать источники, темы или метрики.
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
output\...\discovery_manifest.md
output\...\source_candidates_review.md
output\...\batch_summary.md
```

В `discovery_manifest.md` видно, годится ли партия как source-first batch. В `source_candidates_review.md` видны исходные ссылки и причины допуска. В `batch_summary.md` видно качество партии, платформы, темы, причины отсева, топ-10 по `final_score`, топ-5 по `neuropravo_fit_score` и блок `Смотреть первыми`.

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

