# Discovery Manifest

Входной CSV: `D:\Projects\Others\NeuroPravo_Shorts_Signal_Automation\data\source_acquisition\24-72h\discovery_2026-07-12_24-72h.csv`
Окно свежести по данным: `24-72h`
Metrics mode: `public_search`
Порог final_score: `55`
Сгенерировано локально: 2026-07-12 20:25

Это паспорт партии для Окна 1. Он проверяет источник и регулярность поиска до сценариев.

## Gate

- Status: `SOURCE-REVIEW-READY`
- Всего кандидатов: 24
- Отобрано генератором: 13
- Тем покрыто: 8
- Строк с видимым публичным сигналом: 13
- Ошибок валидации: 0

## Acceptance checks

- Минимум кандидатов до scoring: 12
- Минимум тем: 3
- Минимум строк с видимым сигналом: 5
- Обязательные файлы после прогона: `discovery_manifest.md`, `source_candidates_review.md`, `batch_summary.md`

## Blockers

- Нет. Партию можно читать в `source_candidates_review.md`.

## Controller decision

Окно 1 может передать только кандидатов из `source_candidates_review.md` со статусом `ЗАЛЕТЕВШИЙ-КАНДИДАТ` или вручную подтвержденным `ПОТЕНЦИАЛЬНЫЙ-СИГНАЛ`.

## Freshness windows to maintain

- `24-72h`: Catch early spikes before they become obvious. CSV `data/source_acquisition/24-72h/discovery_YYYY-MM-DD_24-72h.csv`, output `output/discovery_YYYY-MM-DD_24-72h`.
- `7d`: Find candidates with enough traction and still-current context. CSV `data/source_acquisition/7d/discovery_YYYY-MM-DD_7d.csv`, output `output/discovery_YYYY-MM-DD_7d`.
- `30d`: Map durable themes and compare topics across the month. CSV `data/source_acquisition/30d/discovery_YYYY-MM-DD_30d.csv`, output `output/discovery_YYYY-MM-DD_30d`.
