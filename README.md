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

## Порог отбора

По умолчанию отбираются ролики с `final_score >= 70` и достаточной привязкой к темам НейроПраво.

Изменить порог:

```powershell
python .\scripts\generate_cards.py --input data\input_videos.csv --out output --min-score 70
python .\scripts\generate_cards.py --input data\input_videos.csv --out output --min-score 80
```

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
