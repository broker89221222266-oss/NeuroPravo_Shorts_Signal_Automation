# Scoring Calibration Note - Public Search Batch 2026-07-12

Input:
`data\manual_batches\batch_2026-07-12.csv`

Command:
```powershell
python .\scripts\generate_cards.py --input data\manual_batches\batch_2026-07-12.csv --out output\first_real_batch_2026-07-12_public_search --min-score 55 --metrics-mode public_search
```

## Result

- Total rows: 24.
- Validation issues: 0.
- Old normal run at `--min-score 70`: 0 selected.
- New `public_search` run at `--min-score 55`: 13 selected.
- Data quality: views are visible, but likes/comments are unknown for all rows; published_at is approximate collection date.

## What changed in scoring

- Unknown likes/comments are not treated as a negative engagement signal in `public_search` mode.
- Views and `neuropravo_fit_score` carry more weight than engagement.
- `recency_quality` is marked as `approximate` when notes say the date is approximate or collection-date based.
- Rows with incomplete public metrics need an additional visible public signal: at least 5000 views, or strong fit with at least 800 views.
- Output now includes `metrics_mode`, `metrics_completeness`, and `recency_quality`.

## Comparison With Manual Editor Review

Manual top-5:

1. Debt under receipt: `https://www.youtube.com/shorts/ZKugZyG9T0U`
2. Builders / advance payment: `https://www.youtube.com/shorts/WABbFASESlw`
3. Client does not pay: `https://www.youtube.com/shorts/FytHW96ECts`
4. WB / product return: `https://www.youtube.com/shorts/AI1mkREPTH0`
5. Alimony: `https://www.youtube.com/shorts/3PUGbLg524c`

Public-search result:

- All 5 manual ideas are selected.
- 4 of 5 manual ideas are in the automatic top-5 by `final_score`.
- The only extra idea that entered top-5 is another debt/receipt candidate with strong fit and views.
- The three manual “take to work” ideas are selected: debt under receipt, builders/advance, client does not pay.

## Calibration Decision

The new mode is good enough for public-search batches. It should be treated as an editorial shortlist, not as proof of real engagement.

Recommended thresholds:

- `normal`: `--min-score 70` for complete imports with real dates and engagement metrics.
- `public_search`: `--min-score 55` for open search batches with views but unknown likes/comments/dates.

No broader rewrite is needed now. Next calibration should happen only after Alexander manually watches the top candidates and marks which hooks actually work.
