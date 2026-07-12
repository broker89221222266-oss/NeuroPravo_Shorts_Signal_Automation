# Архитектура MVP: import-first слой

## Текущая среда

Рабочая папка:

```text
D:\Projects\Others\NeuroPravo_Shorts_Signal_Automation
```

Repo:

```text
https://github.com/broker89221222266-oss/NeuroPravo_Shorts_Signal_Automation
```

Текущий слой не собирает данные из платформ сам. Он принимает CSV, проверяет его, считает score и формирует карточки сценариев.

## Контракт входного CSV

Обязательные поля:

```text
source_url, platform, published_at, author, title_or_caption, views, likes, comments, shares, saves, duration_sec, topic_hint, notes
```

Источники CSV:

- ручной отбор Александра;
- Apify export;
- ViewStats export;
- будущий YouTube Data API export;
- любая таблица, приведенная к шаблону `data\templates\import_template.csv`.

## Валидация

Генератор проверяет:

- все обязательные поля есть;
- `source_url` не пустой;
- `platform` входит в разрешенный список;
- `published_at` в формате `YYYY-MM-DD`, `DD.MM.YYYY` или `YYYY/MM/DD`;
- дата не старше 30 дней и не в будущем;
- числовые поля корректно парсятся;
- длительность не превышает лимит short/reels-карточки при отборе.

Ошибки пишутся в:

```text
output\validation_report.csv
```

## Scoring

Для каждого валидного ролика считаются:

- `raw_score` - грубая сила метрик;
- `engagement_score` - вовлеченность относительно просмотров;
- `recency_score` - свежесть внутри 30-дневного окна;
- `neuropravo_fit_score` - совпадение с темами НейроПраво и конфликтными сигналами;
- `final_score` - итоговый score 0-100.

Формула `final_score`:

```text
raw_score 35% + engagement_score 20% + recency_score 20% + neuropravo_fit_score 25%
```

`raw_score` перед взвешиванием логарифмически нормализуется, чтобы один крупный ролик не задавил все остальное.

## Выходы

Каждый запуск создает:

```text
scenario_cards.md
scenario_cards.csv
scenario_cards.json
validation_report.csv
```

Markdown предназначен для чтения и ручного выбора. CSV/JSON - для дальнейшей автоматизации или загрузки в таблицу.

## Безопасность

- не публиковать автоматически;
- не рендерить видео;
- не загружать в аккаунты;
- не подключать платные API, логины, токены и cookies без отдельной команды Александра;
- не копировать чужой текст;
- не обещать юридический результат;
- не хранить секреты в GitHub, README, CSV или памяти.

## Следующие возможные слои

1. Подключить реальный экспорт YouTube Shorts в CSV.
2. Подключить Apify export parser только после отдельной команды.
3. Добавить Google Sheets/Airtable как optional output.
4. Заменить локальную эвристику сценариев на LLM-вызов, сохранив текущий CSV/JSON contract.
