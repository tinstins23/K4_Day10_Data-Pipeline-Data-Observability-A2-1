from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text

METRIC_KEYS = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, bool):
        return "pass" if value else "fail"
    return str(value)


def _delta(before: Any, after: Any) -> str:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return f"{after - before:+.4f}"
    return "N/A"


def _source_section(source_summary: dict[str, Any]) -> list[str]:
    lines = ["## Source summary", ""]
    if not source_summary:
        lines.extend(["_No source summary provided._", ""])
        return lines
    for key, value in source_summary.items():
        lines.append(f"- **{key}:** `{_fmt(value)}`")
    lines.append("")
    return lines


def _metrics_section(title: str, metrics: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", ""]
    lines.append("| Metric | Value |")
    lines.append("| --- | ---: |")
    for key in METRIC_KEYS:
        lines.append(f"| `{key}` | {_fmt(metrics.get(key))} |")
    if "samples" in metrics:
        lines.append(f"| `samples` | {_fmt(metrics.get('samples'))} |")
    lines.append("")
    if "ragas" in metrics:
        lines.extend(["### Ragas", "", f"```json\n{metrics['ragas']}\n```", ""])
    return lines


def _quality_section(title: str, quality: dict[str, Any]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"- **Success:** `{_fmt(quality.get('success'))}`",
        f"- **Row count:** `{_fmt(quality.get('row_count'))}`",
        f"- **Failed checks:** `{_fmt(quality.get('failed_checks') or [])}`",
        "",
    ]
    checks = quality.get("checks") or []
    if checks:
        lines.extend(
            [
                "| Check | Dimension | Passed | Expected | Actual |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for check in checks:
            lines.append(
                "| {name} | {dimension} | {passed} | {expected} | {actual} |".format(
                    name=check.get("name"),
                    dimension=check.get("dimension"),
                    passed=check.get("passed"),
                    expected=check.get("expected"),
                    actual=check.get("actual"),
                )
            )
        lines.append("")
    return lines


def _freshness_section(title: str, freshness: dict[str, Any]) -> list[str]:
    return [
        f"## {title}",
        "",
        f"- **is_fresh:** `{_fmt(freshness.get('is_fresh'))}`",
        f"- **latest_published:** `{_fmt(freshness.get('latest_published'))}`",
        f"- **oldest_published:** `{_fmt(freshness.get('oldest_published'))}`",
        f"- **stale_rows:** `{_fmt(freshness.get('stale_rows'))}` / `{_fmt(freshness.get('total_rows'))}`",
        f"- **freshness_threshold_days:** `{_fmt(freshness.get('freshness_threshold_days'))}`",
        f"- **max_age_days:** `{_fmt(freshness.get('max_age_days'))}`",
        f"- **mean_age_days:** `{_fmt(freshness.get('mean_age_days'))}`",
        "",
    ]


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report cho baseline phase.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    lines: list[str] = [
        "# Phase 1 Baseline Report",
        "",
        "Baseline pipeline report: source -> evaluation metrics -> data quality -> freshness.",
        "",
    ]
    lines.extend(_source_section(source_summary))
    lines.extend(_metrics_section("Evaluation metrics", metrics))
    lines.extend(_quality_section("Data quality", quality))
    lines.extend(_freshness_section("Freshness", freshness))
    write_text(Path(report_path), "\n".join(lines))


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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    lines: list[str] = [
        "# Corruption Comparison Report",
        "",
        "So sánh metrics, data quality và freshness giữa baseline, corrupted và repaired.",
        "",
        "## Metrics comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Δ corrupt | Δ repair |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in METRIC_KEYS:
        base = baseline_metrics.get(key)
        corrupt = corrupted_metrics.get(key)
        repair = repaired_metrics.get(key)
        lines.append(
            f"| `{key}` | {_fmt(base)} | {_fmt(corrupt)} | {_fmt(repair)} | "
            f"{_delta(base, corrupt)} | {_delta(corrupt, repair)} |"
        )
    lines.extend(
        [
            "",
            "## Quality & freshness comparison",
            "",
            "| Signal | Corrupted | Repaired |",
            "| --- | --- | --- |",
            f"| Quality success | `{_fmt(corrupted_quality.get('success'))}` | `{_fmt(repaired_quality.get('success'))}` |",
            f"| Failed checks | `{_fmt(corrupted_quality.get('failed_checks') or [])}` | `{_fmt(repaired_quality.get('failed_checks') or [])}` |",
            f"| Freshness is_fresh | `{_fmt(corrupted_freshness.get('is_fresh'))}` | `{_fmt(repaired_freshness.get('is_fresh'))}` |",
            f"| Stale rows | `{_fmt(corrupted_freshness.get('stale_rows'))}` | `{_fmt(repaired_freshness.get('stale_rows'))}` |",
            "",
        ]
    )
    lines.extend(_quality_section("Corrupted data quality", corrupted_quality))
    lines.extend(_freshness_section("Corrupted freshness", corrupted_freshness))
    lines.extend(_quality_section("Repaired data quality", repaired_quality))
    lines.extend(_freshness_section("Repaired freshness", repaired_freshness))
    write_text(Path(report_path), "\n".join(lines))
