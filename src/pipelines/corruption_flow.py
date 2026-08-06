from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json, write_text
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records


METRIC_NAMES = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _load_phase2_dependencies():
    """Load retrieval/evaluation only when Phase 2 reaches those steps.

    This prevents the script from failing at module import time and gives a
    clearer error when the project's optional runtime dependencies are missing.
    """
    try:
        from evaluation.metrics import evaluate_pipeline
        from retrieval.index import LocalEmbeddingIndex
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        raise RuntimeError(
            "Phase 2 reached the retrieval/evaluation step, but the Python "
            f"environment is missing package '{missing}'.\n"
            "Install the project dependencies in the active virtual environment:\n"
            "    python -m pip install -e .\n"
            "This is an environment dependency error, not a corruption logic error."
        ) from exc

    return evaluate_pipeline, LocalEmbeddingIndex


def _require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise RuntimeError(
            f"Missing {description}: {path}\n"
            "Run Phase 1 first or ask the responsible team member to generate it."
        )


def _read_optional_json(path: Path) -> dict[str, Any]:
    """Read a JSON artifact when available; otherwise return an empty payload."""
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _load_clean_dataframe(path: Path) -> pd.DataFrame:
    _require_file(path, "baseline clean CSV")
    df = pd.read_csv(path)
    if df.empty:
        raise RuntimeError(f"Baseline clean CSV is empty: {path}")
    return df


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _quality_snapshot(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    """Compute Phase-2 comparison checks without modifying Member 3 files."""

    paper_ids = df.get("paper_id", pd.Series(dtype="object"))
    titles = df.get("title", pd.Series(dtype="object"))
    summaries = df.get("summary", pd.Series(dtype="object"))
    ages = pd.to_numeric(
        df.get("age_days", pd.Series(dtype="float64")),
        errors="coerce",
    )

    total_rows = int(len(df))
    null_paper_ids = int(paper_ids.isna().sum())
    duplicate_paper_ids = int(paper_ids.astype(str).duplicated().sum())
    blank_titles = int(titles.fillna("").astype(str).str.strip().eq("").sum())
    blank_summaries = int(summaries.fillna("").astype(str).str.strip().eq("").sum())
    short_summaries = int(
        summaries.fillna("").astype(str).str.len().lt(80).sum()
    )
    stale_rows = int((ages > settings.freshness_threshold_days).fillna(False).sum())

    checks = {
        "row_count_positive": total_rows > 0,
        "paper_id_not_null": null_paper_ids == 0,
        "paper_id_unique": duplicate_paper_ids == 0,
        "title_not_blank": blank_titles == 0,
        "summary_not_blank": blank_summaries == 0,
        "summary_min_length": short_summaries == 0,
        "freshness_threshold": stale_rows == 0,
    }

    payload = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": total_rows,
        "passed": all(checks.values()),
        "checks": checks,
        "details": {
            "null_paper_ids": null_paper_ids,
            "duplicate_paper_ids": duplicate_paper_ids,
            "blank_titles": blank_titles,
            "blank_summaries": blank_summaries,
            "short_summaries": short_summaries,
            "stale_rows": stale_rows,
            "freshness_threshold_days": settings.freshness_threshold_days,
        },
    }

    write_json(settings.paths.quality_dir / f"{report_name}.json", payload)
    return payload


def _freshness_snapshot(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    published = pd.to_datetime(df.get("published"), errors="coerce", utc=True)
    ages = pd.to_numeric(
        df.get("age_days", pd.Series(dtype="float64")),
        errors="coerce",
    )
    stale_rows = int((ages > settings.freshness_threshold_days).fillna(False).sum())

    payload = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "latest_published": (
            published.max().date().isoformat() if published.notna().any() else None
        ),
        "oldest_published": (
            published.min().date().isoformat() if published.notna().any() else None
        ),
        "stale_rows": stale_rows,
        "total_rows": int(len(df)),
        "is_fresh": stale_rows == 0,
        "freshness_threshold_days": settings.freshness_threshold_days,
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", payload)
    return payload


def _repair_from_raw(settings: Settings) -> pd.DataFrame:
    """Rebuild repaired data from the immutable raw records snapshot."""

    _require_file(settings.paths.raw_records_json, "raw Crossref records snapshot")
    records = load_raw_records(settings.paths.raw_records_json)
    if not records:
        raise RuntimeError(
            f"Raw snapshot contains no records: {settings.paths.raw_records_json}"
        )
    return build_clean_dataframe(records, run_date=datetime.now(UTC))


def _metric_value(metrics: dict[str, Any], name: str) -> float | None:
    value = metrics.get(name)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _format_number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def _generate_comparison_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    lines = [
        "# Corruption, Repair and Reliability Report",
        "",
        f"Generated at: `{datetime.now(UTC).isoformat()}`",
        "",
        "## 1. Evaluation comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for name in METRIC_NAMES:
        baseline = _metric_value(baseline_metrics, name)
        corrupted = _metric_value(corrupted_metrics, name)
        repaired = _metric_value(repaired_metrics, name)
        corruption_delta = (
            corrupted - baseline if corrupted is not None and baseline is not None else None
        )
        repair_delta = (
            repaired - corrupted if repaired is not None and corrupted is not None else None
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    _format_number(baseline),
                    _format_number(corrupted),
                    _format_number(repaired),
                    _format_number(corruption_delta),
                    _format_number(repair_delta),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 2. Data quality comparison",
            "",
            f"- Corrupted quality passed: **{corrupted_quality['passed']}**",
            f"- Repaired quality passed: **{repaired_quality['passed']}**",
            f"- Corrupted duplicate paper IDs: **{corrupted_quality['details']['duplicate_paper_ids']}**",
            f"- Repaired duplicate paper IDs: **{repaired_quality['details']['duplicate_paper_ids']}**",
            f"- Corrupted blank summaries: **{corrupted_quality['details']['blank_summaries']}**",
            f"- Repaired blank summaries: **{repaired_quality['details']['blank_summaries']}**",
            "",
            "## 3. Freshness comparison",
            "",
            f"- Corrupted stale rows: **{corrupted_freshness['stale_rows']} / {corrupted_freshness['total_rows']}**",
            f"- Repaired stale rows: **{repaired_freshness['stale_rows']} / {repaired_freshness['total_rows']}**",
            f"- Corrupted latest publication: `{corrupted_freshness['latest_published']}`",
            f"- Repaired latest publication: `{repaired_freshness['latest_published']}`",
            "",
            "## 4. Reliability conclusion",
            "",
            "The corrupted corpus is expected to show measurable degradation in retrieval, answer quality, uniqueness, completeness, or freshness. The repaired corpus is rebuilt from the raw Crossref snapshot rather than edited in place, so its metrics should move back toward the baseline state.",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))


def main() -> None:
    settings = load_settings()

    # Member 4 can start before Phase 1 evaluation is complete.
    # Clean data and raw records are still real required inputs:
    # - clean CSV is the source to corrupt
    # - raw snapshot is the immutable source used for repair
    _require_file(settings.paths.clean_csv, "baseline clean CSV")
    _require_file(settings.paths.raw_records_json, "raw Crossref records snapshot")

    baseline_metrics = _read_optional_json(settings.paths.baseline_metrics)
    clean_df = _load_clean_dataframe(settings.paths.clean_csv)

    evaluation_ready = (
        settings.paths.baseline_metrics.exists()
        and settings.paths.eval_testset.exists()
    )

    evaluate_pipeline = None
    LocalEmbeddingIndex = None

    if evaluation_ready:
        evaluate_pipeline, LocalEmbeddingIndex = _load_phase2_dependencies()
    else:
        print(
            "Phase 1 evaluation artifacts are not ready. "
            "Running Member 4 in data-only mode."
        )
        if not settings.paths.baseline_metrics.exists():
            print(f"- Missing baseline metrics: {settings.paths.baseline_metrics}")
        if not settings.paths.eval_testset.exists():
            print(f"- Missing evaluation test set: {settings.paths.eval_testset}")

    # Corrupt and persist. Index/evaluation run only when Phase 1 artifacts exist.
    corrupted_df = corrupt_clean_dataframe(
        clean_df,
        output_log_path=settings.paths.corruption_log,
    )
    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )
    corrupted_metrics: dict[str, Any] = {}

    if evaluation_ready and LocalEmbeddingIndex is not None and evaluate_pipeline is not None:
        corrupted_index = LocalEmbeddingIndex.build(
            corrupted_df,
            settings=settings,
            embeddings_output_path=settings.paths.corrupted_embeddings_json,
        )
        corrupted_bundle = evaluate_pipeline(
            settings=settings,
            index=corrupted_index,
            test_set_path=settings.paths.eval_testset,
            metrics_output_path=settings.paths.corrupted_metrics,
            answers_output_path=settings.paths.corrupted_answers,
        )
        corrupted_metrics = corrupted_bundle.summary
    else:
        write_json(
            settings.paths.corrupted_metrics,
            {
                "status": "skipped",
                "reason": "Phase 1 baseline metrics or evaluation test set is not available.",
            },
        )
    corrupted_quality = _quality_snapshot(
        corrupted_df,
        settings,
        report_name="corrupted_quality",
    )
    corrupted_freshness = _freshness_snapshot(
        corrupted_df,
        settings,
        report_name="corrupted_freshness",
    )

    # Repair from raw records, never from the corrupted dataframe.
    repaired_df = _repair_from_raw(settings)
    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )
    repaired_metrics: dict[str, Any] = {}

    if evaluation_ready and LocalEmbeddingIndex is not None and evaluate_pipeline is not None:
        repaired_index = LocalEmbeddingIndex.build(
            repaired_df,
            settings=settings,
            embeddings_output_path=settings.paths.repaired_embeddings_json,
        )
        repaired_bundle = evaluate_pipeline(
            settings=settings,
            index=repaired_index,
            test_set_path=settings.paths.eval_testset,
            metrics_output_path=settings.paths.repaired_metrics,
            answers_output_path=settings.paths.repaired_answers,
        )
        repaired_metrics = repaired_bundle.summary
    else:
        write_json(
            settings.paths.repaired_metrics,
            {
                "status": "skipped",
                "reason": "Phase 1 baseline metrics or evaluation test set is not available.",
            },
        )
    repaired_quality = _quality_snapshot(
        repaired_df,
        settings,
        report_name="repaired_quality",
    )
    repaired_freshness = _freshness_snapshot(
        repaired_df,
        settings,
        report_name="repaired_freshness",
    )

    _generate_comparison_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("Phase 2 Member 4 flow completed successfully.")
    print(f"Corruption log: {settings.paths.corruption_log}")
    print(f"Corrupted data: {settings.paths.corrupted_clean_csv}")
    print(f"Repaired data: {settings.paths.repaired_clean_csv}")
    print(f"Corrupted metrics/status: {settings.paths.corrupted_metrics}")
    print(f"Repaired metrics/status: {settings.paths.repaired_metrics}")
    print(f"Comparison report: {settings.paths.comparison_report}")
    if not evaluation_ready:
        print(
            "Evaluation was skipped. Run this script again after Phase 1 creates "
            "baseline_metrics.json and test_set.json."
        )


if __name__ == "__main__":
    main()