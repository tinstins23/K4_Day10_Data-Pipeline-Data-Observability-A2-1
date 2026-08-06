# Corruption Comparison Report

So sánh metrics, data quality và freshness giữa baseline, corrupted và repaired.

## Metrics comparison

| Metric | Baseline | Corrupted | Repaired | Δ corrupt | Δ repair |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 0.7500 | 0.4000 | 0.7200 | -0.3500 | +0.3200 |
| `mean_token_f1` | 0.6100 | 0.3000 | 0.5800 | -0.3100 | +0.2800 |
| `judge_accuracy` | 0.7000 | 0.4000 | 0.6800 | -0.3000 | +0.2800 |
| `mean_judge_score` | 3.5000 | 2.1000 | 3.4000 | -1.4000 | +1.3000 |

## Quality & freshness comparison

| Signal | Corrupted | Repaired |
| --- | --- | --- |
| Quality success | `fail` | `pass` |
| Failed checks | `['summary_min_length']` | `[]` |
| Freshness is_fresh | `fail` | `pass` |
| Stale rows | `3` | `0` |

## Corrupted data quality

- **Success:** `fail`
- **Row count:** `N/A`
- **Failed checks:** `['summary_min_length']`

## Corrupted freshness

- **is_fresh:** `fail`
- **latest_published:** `N/A`
- **oldest_published:** `N/A`
- **stale_rows:** `3` / `N/A`
- **freshness_threshold_days:** `N/A`
- **max_age_days:** `N/A`
- **mean_age_days:** `N/A`

## Repaired data quality

- **Success:** `pass`
- **Row count:** `N/A`
- **Failed checks:** `[]`

## Repaired freshness

- **is_fresh:** `pass`
- **latest_published:** `N/A`
- **oldest_published:** `N/A`
- **stale_rows:** `0` / `N/A`
- **freshness_threshold_days:** `N/A`
- **max_age_days:** `N/A`
- **mean_age_days:** `N/A`
