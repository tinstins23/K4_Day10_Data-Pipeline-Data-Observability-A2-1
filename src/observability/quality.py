from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json

MIN_SUMMARY_CHARS = 40


def _series_is_blank(series: pd.Series) -> pd.Series:
    as_str = series.fillna("").astype(str).str.strip()
    return as_str.eq("") | as_str.str.lower().isin({"nan", "none", "null"})


def _summary_lengths(df: pd.DataFrame) -> pd.Series:
    if "summary_chars" in df.columns:
        return pd.to_numeric(df["summary_chars"], errors="coerce").fillna(0).astype(int)
    if "summary" in df.columns:
        return df["summary"].fillna("").astype(str).str.strip().str.len()
    return pd.Series([0] * len(df), index=df.index, dtype=int)


def _age_days(df: pd.DataFrame) -> pd.Series:
    if "age_days" in df.columns:
        return pd.to_numeric(df["age_days"], errors="coerce")
    if "published" in df.columns:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
        now = pd.Timestamp.now(tz="UTC")
        return (now - published).dt.days
    return pd.Series([pd.NA] * len(df), index=df.index)


def _check(
    name: str,
    dimension: str,
    passed: bool,
    expected: Any,
    actual: Any,
    details: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "dimension": dimension,
        "passed": bool(passed),
        "expected": expected,
        "actual": actual,
        "details": details,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """TODO(student): tao bo data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    row_count = int(len(df))
    threshold = int(settings.freshness_threshold_days)
    checks: list[dict[str, Any]] = []

    # 1. Check row count.
    checks.append(
        _check(
            name="row_count_positive",
            dimension="completeness",
            passed=row_count > 0,
            expected="> 0",
            actual=row_count,
            details="Dataset must contain at least one row.",
        )
    )

    # 2. Check `paper_id` not null va unique.
    if "paper_id" not in df.columns:
        checks.append(
            _check(
                name="paper_id_present",
                dimension="schema",
                passed=False,
                expected="column paper_id",
                actual="missing",
                details="Missing required column paper_id.",
            )
        )
    else:
        null_paper_ids = int(_series_is_blank(df["paper_id"]).sum())
        duplicate_paper_ids = int(
            df["paper_id"].fillna("").astype(str).str.strip().duplicated().sum()
        )
        checks.append(
            _check(
                name="paper_id_not_null",
                dimension="completeness",
                passed=null_paper_ids == 0,
                expected=0,
                actual=null_paper_ids,
                details="Count of rows with missing paper_id.",
            )
        )
        checks.append(
            _check(
                name="paper_id_unique",
                dimension="uniqueness",
                passed=duplicate_paper_ids == 0,
                expected=0,
                actual=duplicate_paper_ids,
                details="Count of duplicate paper_id values.",
            )
        )

    # 3. Check `title` not null.
    if "title" not in df.columns:
        checks.append(
            _check(
                name="title_present",
                dimension="schema",
                passed=False,
                expected="column title",
                actual="missing",
                details="Missing required column title.",
            )
        )
    else:
        null_titles = int(_series_is_blank(df["title"]).sum())
        checks.append(
            _check(
                name="title_not_null",
                dimension="completeness",
                passed=null_titles == 0,
                expected=0,
                actual=null_titles,
                details="Count of rows with missing title.",
            )
        )

    # 4. Check do dai `summary`.
    summary_lengths = _summary_lengths(df)
    short_summaries = int((summary_lengths < MIN_SUMMARY_CHARS).sum()) if row_count else 0
    checks.append(
        _check(
            name="summary_min_length",
            dimension="validity",
            passed=bool(short_summaries == 0 and row_count > 0),
            expected=f">= {MIN_SUMMARY_CHARS} chars for all rows",
            actual={
                "short_rows": short_summaries,
                "min_chars": int(summary_lengths.min()) if row_count else 0,
                "median_chars": float(summary_lengths.median()) if row_count else 0.0,
            },
            details=f"Summaries shorter than {MIN_SUMMARY_CHARS} characters fail.",
        )
    )

    # 5. Check freshness bang `age_days`.
    ages = _age_days(df)
    valid_ages = ages.dropna()
    stale_rows = int((ages > threshold).fillna(False).sum()) if row_count else 0
    missing_age = int(ages.isna().sum()) if row_count else 0
    checks.append(
        _check(
            name="freshness_age_days",
            dimension="freshness",
            passed=bool(stale_rows == 0 and missing_age == 0 and row_count > 0),
            expected=f"age_days <= {threshold} for all rows",
            actual={
                "stale_rows": stale_rows,
                "missing_age_rows": missing_age,
                "max_age_days": int(valid_ages.max()) if not valid_ages.empty else None,
            },
            details="Rows with age_days above freshness_threshold_days are stale.",
        )
    )

    # 6. Ghi ket qua vao `data/quality/`.
    success = bool(all(item["passed"] for item in checks))
    artifact_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    payload: dict[str, Any] = {
        "report_name": report_name,
        "success": success,
        "row_count": row_count,
        "freshness_threshold_days": threshold,
        "min_summary_chars": MIN_SUMMARY_CHARS,
        "failed_checks": [item["name"] for item in checks if not item["passed"]],
        "checks": checks,
        "artifact_path": str(artifact_path),
    }
    write_json(artifact_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """TODO(student): tong hop freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    path = Path(report_path)
    threshold = int(settings.freshness_threshold_days)
    total_rows = int(len(df))
    ages = _age_days(df)
    stale_rows = int((ages > threshold).fillna(False).sum()) if total_rows else 0

    # 1. Tim latest va oldest published date.
    latest_published: str | None = None
    oldest_published: str | None = None
    if "published" in df.columns and total_rows:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
        if published.notna().any():
            latest_published = published.max().date().isoformat()
            oldest_published = published.min().date().isoformat()

    # 2-3. Dem stale rows + tao payload.
    valid_ages = ages.dropna()
    ages_complete = bool(ages.notna().all()) if total_rows else False
    payload: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": bool(total_rows > 0 and stale_rows == 0 and ages_complete),
        "freshness_threshold_days": threshold,
        "max_age_days": int(valid_ages.max()) if not valid_ages.empty else None,
        "mean_age_days": float(valid_ages.mean()) if not valid_ages.empty else None,
        "artifact_path": str(path),
    }

    # 4. Ghi JSON report.
    write_json(path, payload)
    return payload
