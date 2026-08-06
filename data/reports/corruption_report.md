# Corruption, Repair and Reliability Report

Generated at: `2026-08-06T09:35:46.402192+00:00`

## 1. Evaluation comparison

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |
|---|---:|---:|---:|---:|---:|
| retrieval_hit_rate | 1.0000 | 0.6250 | 1.0000 | -0.3750 | 0.3750 |
| mean_token_f1 | 1.0000 | 0.5028 | 1.0000 | -0.4972 | 0.4972 |
| judge_accuracy | 1.0000 | 0.5000 | 1.0000 | -0.5000 | 0.5000 |
| mean_judge_score | 5.0000 | 3.0833 | 5.0000 | -1.9167 | 1.9167 |

## 2. Data quality comparison

- Corrupted quality passed: **False**
- Repaired quality passed: **True**
- Corrupted duplicate paper IDs: **3**
- Repaired duplicate paper IDs: **0**
- Corrupted blank summaries: **6**
- Repaired blank summaries: **0**

## 3. Freshness comparison

- Corrupted stale rows: **3 / 24**
- Repaired stale rows: **0 / 24**
- Corrupted latest publication: `2026-07-10`
- Repaired latest publication: `2026-08-01`

## 4. Reliability conclusion

The corrupted corpus is expected to show measurable degradation in retrieval, answer quality, uniqueness, completeness, or freshness. The repaired corpus is rebuilt from the raw Crossref snapshot rather than edited in place, so its metrics should move back toward the baseline state.
