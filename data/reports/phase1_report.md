# Phase 1 Baseline Report

Baseline pipeline report: source -> evaluation metrics -> data quality -> freshness.

## Source summary

- **source_api:** `Crossref REST API`
- **source_query:** `agentic retrieval augmented generation large language model`
- **source_filter:** `from-pub-date:2026-02-07,has-abstract:true`
- **source_mode:** `loaded_snapshot`
- **raw_record_count:** `24`
- **clean_record_count:** `24`
- **test_set_mode:** `loaded`
- **test_set_size:** `24`
- **collection_name:** `papers-baseline`
- **embedding_model:** `sentence-transformers/all-MiniLM-L6-v2`

## Evaluation metrics

| Metric | Value |
| --- | ---: |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 0.6667 |
| `judge_accuracy` | 0.6667 |
| `mean_judge_score` | 3.6667 |
| `samples` | 24 |

### Ragas

```json
{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}
```

## Data quality

- **Success:** `pass`
- **Row count:** `24`
- **Failed checks:** `[]`

| Check | Dimension | Passed | Expected | Actual |
| --- | --- | --- | --- | --- |
| row_count_positive | completeness | True | > 0 | 24 |
| paper_id_not_null | completeness | True | 0 | 0 |
| paper_id_unique | uniqueness | True | 0 | 0 |
| title_not_null | completeness | True | 0 | 0 |
| summary_min_length | validity | True | >= 40 chars for all rows | {'short_rows': 0, 'min_chars': 834, 'median_chars': 1661.0} |
| freshness_age_days | freshness | True | age_days <= 180 for all rows | {'stale_rows': 0, 'missing_age_rows': 0, 'max_age_days': 175} |

## Freshness

- **is_fresh:** `pass`
- **latest_published:** `2026-08-01`
- **oldest_published:** `2026-02-12`
- **stale_rows:** `0` / `24`
- **freshness_threshold_days:** `180`
- **max_age_days:** `175`
- **mean_age_days:** `76.5833`
