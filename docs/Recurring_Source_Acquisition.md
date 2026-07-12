# Recurring Source Acquisition

Дата фиксации: 2026-07-12

Цель: регулярно находить исходные short/reels-сигналы для НейроПраво и не переходить к сценариям, пока источник не проверен.

## Главный порядок

1. Собрать публичные кандидаты без логина, API, cookies, токенов, скачивания видео и платных сервисов.
2. Заполнить одну из трех source acquisition партий.
3. Запустить генератор.
4. Сначала открыть `discovery_manifest.md`.
5. Затем открыть `source_candidates_review.md`.
6. Только после source review решать, можно ли отдавать кандидата Окну 2 на сценарий.

`source_candidates_review.md` идет раньше сценариев всегда.

## Где лежат партии

```text
data\source_acquisition\24-72h\discovery_YYYY-MM-DD_24-72h.csv
data\source_acquisition\7d\discovery_YYYY-MM-DD_7d.csv
data\source_acquisition\30d\discovery_YYYY-MM-DD_30d.csv
```

Шаблоны уже лежат в этих папках. Перед сбором скопируйте шаблон и замените `YYYY-MM-DD` на дату сбора.

## 24-72h fresh scan

Цель: поймать ранние вспышки до того, как они стали очевидными.

Минимум: 8 кандидатов. Лучше: 15 кандидатов.

Что важнее всего:

- свежесть;
- views;
- заметка о скорости роста, если видна;
- тема и конфликт;
- почему это может быть ранний сигнал.

Команда анализа:

```powershell
python .\scripts\generate_cards.py --input data\source_acquisition\24-72h\discovery_2026-07-12_24-72h.csv --out output\discovery_2026-07-12_24-72h --min-score 55 --metrics-mode public_search
```

Первым смотреть:

```text
output\discovery_2026-07-12_24-72h\discovery_manifest.md
output\discovery_2026-07-12_24-72h\source_candidates_review.md
```

## 7d weekly scan

Цель: найти ролики, которые уже набрали traction за неделю и еще актуальны.

Минимум: 12 кандидатов. Лучше: 25 кандидатов.

Что важнее всего:

- views;
- likes/comments, если видны;
- published_at;
- topic_hint;
- notes с объяснением, почему это не случайная выдача.

Команда для public search:

```powershell
python .\scripts\generate_cards.py --input data\source_acquisition\7d\discovery_2026-07-12_7d.csv --out output\discovery_2026-07-12_7d --min-score 55 --metrics-mode public_search
```

Команда для полной выгрузки с нормальными реакциями:

```powershell
python .\scripts\generate_cards.py --input data\source_acquisition\7d\discovery_2026-07-12_7d.csv --out output\discovery_2026-07-12_7d --min-score 70 --metrics-mode normal
```

Первым смотреть:

```text
output\discovery_2026-07-12_7d\discovery_manifest.md
output\discovery_2026-07-12_7d\source_candidates_review.md
```

## 30d monthly scan

Цель: карта рынка и устойчивых тем за месяц.

Минимум: 20 кандидатов. Лучше: 50 кандидатов.

Что важнее всего:

- сравнение тем между собой;
- повторяющиеся конфликты;
- views и реакции;
- полнота метрик;
- темы, которые реально дают материал: долги, договоры, ремонт, застройщик, возврат товара, маркетплейсы, наследство, алименты.

Команда анализа:

```powershell
python .\scripts\generate_cards.py --input data\source_acquisition\30d\discovery_2026-07-12_30d.csv --out output\discovery_2026-07-12_30d --min-score 55 --metrics-mode public_search
```

Первым смотреть:

```text
output\discovery_2026-07-12_30d\discovery_manifest.md
output\discovery_2026-07-12_30d\source_candidates_review.md
```

## Как обновлять кандидатов

Для каждой партии:

1. Открыть нужный CSV в `data\source_acquisition\...`.
2. Добавить новые публичные ссылки и видимые метрики.
3. Если дата/реакции не видны, честно указать это в `notes`.
4. Не копировать длинные чужие тексты: достаточно короткого title/caption и своей заметки.
5. Запустить команду анализа.
6. Проверить `discovery_manifest.md`: если gate `NEEDS-BETTER-SOURCE-BATCH`, добрать источники и не передавать сценаристу.
7. Проверить `source_candidates_review.md`: только `ЗАЛЕТЕВШИЙ-КАНДИДАТ` или вручную подтвержденный `ПОТЕНЦИАЛЬНЫЙ-СИГНАЛ` может идти дальше.

## Безопасные источники без отдельного разрешения

- ручной public search;
- ViewStats manual export, если файл уже есть у Александра;
- Apify CSV, если он уже экспортирован пользователем и передан как файл.

## Что нельзя без отдельной команды Александра

- запускать YouTube Data API;
- запускать Apify actor;
- логиниться в TikTok, Instagram, YouTube или другие соцсети;
- сохранять cookies, токены, пароли;
- синхронизировать Google Sheets/Airtable;
- скачивать видео;
- рендерить, публиковать или загружать видео.
