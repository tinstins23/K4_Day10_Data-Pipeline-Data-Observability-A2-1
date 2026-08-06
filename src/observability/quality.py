from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run traceable completeness, uniqueness and freshness checks."""
    paper_ids = df.get("paper_id", pd.Series(dtype="object"))
    titles = df.get("title", pd.Series(dtype="object"))
    summaries = df.get("summary", pd.Series(dtype="object"))
    ages = pd.to_numeric(df.get("age_days", pd.Series(dtype="float64")), errors="coerce")
    total_rows = int(len(df))
    null_paper_ids = int(paper_ids.isna().sum() + paper_ids.fillna("").astype(str).str.strip().eq("").sum())
    duplicate_paper_ids = int(paper_ids.fillna("").astype(str).str.strip().duplicated().sum())
    blank_titles = int(titles.fillna("").astype(str).str.strip().eq("").sum())
    blank_summaries = int(summaries.fillna("").astype(str).str.strip().eq("").sum())
    short_summaries = int(summaries.fillna("").astype(str).str.len().lt(80).sum())
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


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarise publication-date freshness using the configured threshold."""
    published = pd.to_datetime(df.get("published", pd.Series(dtype="object")), errors="coerce", utc=True)
    ages = pd.to_numeric(df.get("age_days", pd.Series(dtype="float64")), errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).fillna(False).sum())
    payload = {
        "latest_published": published.max().date().isoformat() if published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
        "stale_rows": stale_rows,
        "total_rows": int(len(df)),
        "is_fresh": stale_rows == 0,
        "freshness_threshold_days": settings.freshness_threshold_days,
    }
    write_json(report_path, payload)
    return payload
