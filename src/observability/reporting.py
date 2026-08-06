from __future__ import annotations

from typing import Any

from core.utils import write_text


METRIC_NAMES = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _number(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else "N/A"


def _detail(payload: dict[str, Any], key: str) -> Any:
    return payload.get("details", {}).get(key, "N/A")


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a baseline report which points only to supplied artifacts."""
    metric_rows = [f"| {name} | {_number(metrics.get(name))} |" for name in METRIC_NAMES]
    quality_rows = [
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in quality.get("checks", {}).items()
    ]
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source summary",
        "",
        *[f"- **{key}**: {value}" for key, value in source_summary.items()],
        "",
        "## Evaluation metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        *metric_rows,
        "",
        "## Data quality",
        "",
        f"Overall status: **{'PASS' if quality.get('passed') else 'FAIL'}**",
        "",
        "| Check | Status |",
        "|---|---|",
        *quality_rows,
        "",
        "## Freshness",
        "",
        f"- Latest publication: `{freshness.get('latest_published')}`",
        f"- Oldest publication: `{freshness.get('oldest_published')}`",
        f"- Stale rows: **{freshness.get('stale_rows', 'N/A')} / {freshness.get('total_rows', 'N/A')}**",
        f"- Threshold: **{freshness.get('freshness_threshold_days', 'N/A')} days**",
        f"- Freshness status: **{'FRESH' if freshness.get('is_fresh') else 'STALE'}**",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write an evidence-led baseline/corrupted/repaired comparison."""
    lines = [
        "# Corruption, Repair and Reliability Report",
        "",
        "## Evaluation comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in METRIC_NAMES:
        baseline = baseline_metrics.get(name)
        corrupted = corrupted_metrics.get(name)
        repaired = repaired_metrics.get(name)
        corruption_delta = corrupted - baseline if isinstance(corrupted, (int, float)) and isinstance(baseline, (int, float)) else None
        repair_delta = repaired - corrupted if isinstance(repaired, (int, float)) and isinstance(corrupted, (int, float)) else None
        lines.append(
            f"| {name} | {_number(baseline)} | {_number(corrupted)} | {_number(repaired)} | {_number(corruption_delta)} | {_number(repair_delta)} |"
        )
    lines.extend([
        "",
        "## Data quality comparison",
        "",
        "| Signal | Corrupted | Repaired |",
        "|---|---:|---:|",
        f"| Overall quality | {'PASS' if corrupted_quality.get('passed') else 'FAIL'} | {'PASS' if repaired_quality.get('passed') else 'FAIL'} |",
        f"| Duplicate paper IDs | {_detail(corrupted_quality, 'duplicate_paper_ids')} | {_detail(repaired_quality, 'duplicate_paper_ids')} |",
        f"| Blank summaries | {_detail(corrupted_quality, 'blank_summaries')} | {_detail(repaired_quality, 'blank_summaries')} |",
        f"| Stale rows | {corrupted_freshness.get('stale_rows', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} |",
        f"| Freshness status | {'FRESH' if corrupted_freshness.get('is_fresh') else 'STALE'} | {'FRESH' if repaired_freshness.get('is_fresh') else 'STALE'} |",
        "",
        "## Interpretation",
        "",
        "Compare this table with the metrics and quality JSON artifacts. Repair is considered evidence-based only when the rebuilt dataset improves the affected signals without changing the shared evaluation set.",
        "",
    ])
    write_text(report_path, "\n".join(lines))
