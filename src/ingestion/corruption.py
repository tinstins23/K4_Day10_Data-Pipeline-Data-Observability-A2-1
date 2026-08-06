from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace, write_json


REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
    "text_for_embedding",
}


def _validate_dataframe(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(
            "Clean dataframe is missing required columns: " + ", ".join(missing)
        )


def _scenario_size(total_rows: int, ratio: float) -> int:
    """Return a deterministic, safe number of rows for one scenario."""
    if total_rows <= 1:
        return 1
    return min(max(1, round(total_rows * ratio)), total_rows - 1)


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {normalize_whitespace(str(row.get('title', '')))}",
            f"Authors: {normalize_whitespace(str(row.get('authors_joined', '')))}",
            f"Categories: {normalize_whitespace(str(row.get('categories_joined', '')))}",
            f"Published: {normalize_whitespace(str(row.get('published', '')))}",
            f"Summary: {normalize_whitespace(str(row.get('summary', '')))}",
        ]
    )


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: Path,
) -> pd.DataFrame:
    """Create a deterministic corrupted copy of a clean paper dataframe.

    The six required scenarios are applied:
    1. delete newest records;
    2. blank summaries;
    3. inject noisy text;
    4. truncate titles;
    5. make publication dates stale;
    6. duplicate records.

    The input dataframe is never modified in place. A detailed JSON log is
    written to ``output_log_path`` so every affected paper can be traced.
    """

    _validate_dataframe(df)

    original = df.copy(deep=True).reset_index(drop=True)
    corrupted = original.copy(deep=True)
    scenarios: list[dict[str, Any]] = []

    # 1. Delete newest records.
    delete_count = _scenario_size(len(corrupted), 0.12)
    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    delete_indices = (
        published.sort_values(ascending=False, na_position="last")
        .index[:delete_count]
        .tolist()
    )
    deleted_ids = corrupted.loc[delete_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=delete_indices).reset_index(drop=True)
    scenarios.append(
        {
            "corruption_type": "delete_newest_records",
            "affected_count": len(deleted_ids),
            "paper_ids": deleted_ids,
            "expected_effect": "Reduced corpus coverage and freshness.",
        }
    )

    if corrupted.empty:
        raise ValueError("Corruption removed all rows; at least two clean rows are required.")

    count = _scenario_size(len(corrupted), 0.15)
    row_indices = corrupted.index.tolist()

    def select(offset: int) -> list[int]:
        return [row_indices[(offset + step) % len(row_indices)] for step in range(count)]

    # 2. Blank summaries.
    blank_indices = select(0)
    blank_ids = corrupted.loc[blank_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[blank_indices, "summary"] = ""
    scenarios.append(
        {
            "corruption_type": "blank_summary",
            "affected_count": len(blank_ids),
            "paper_ids": blank_ids,
            "expected_effect": "Lower summary completeness and answer quality.",
        }
    )

    # 3. Inject text noise.
    noise_indices = select(count)
    noise_ids = corrupted.loc[noise_indices, "paper_id"].astype(str).tolist()
    noise_token = "@@@ CORRUPTED_NOISE_9F3A ### xqzv 000111 !!!"
    for index in noise_indices:
        current = normalize_whitespace(str(corrupted.at[index, "summary"] or ""))
        corrupted.at[index, "summary"] = normalize_whitespace(
            f"{current} {noise_token}"
        )
    scenarios.append(
        {
            "corruption_type": "inject_text_noise",
            "affected_count": len(noise_ids),
            "paper_ids": noise_ids,
            "noise_token": noise_token,
            "expected_effect": "Less stable semantic retrieval precision.",
        }
    )

    # 4. Truncate titles.
    truncate_indices = select(count * 2)
    truncate_ids = corrupted.loc[truncate_indices, "paper_id"].astype(str).tolist()
    max_chars = 12
    for index in truncate_indices:
        title = normalize_whitespace(str(corrupted.at[index, "title"] or ""))
        corrupted.at[index, "title"] = title[:max_chars]
    scenarios.append(
        {
            "corruption_type": "truncate_title",
            "affected_count": len(truncate_ids),
            "paper_ids": truncate_ids,
            "max_characters": max_chars,
            "expected_effect": "Worse title lookup and title-driven retrieval.",
        }
    )

    # 5. Make dates stale.
    stale_indices = select(count * 3)
    stale_ids = corrupted.loc[stale_indices, "paper_id"].astype(str).tolist()
    stale_date = "2000-01-01"
    corrupted.loc[stale_indices, "published"] = stale_date
    if "updated" in corrupted.columns:
        corrupted.loc[stale_indices, "updated"] = stale_date
    scenarios.append(
        {
            "corruption_type": "make_published_date_stale",
            "affected_count": len(stale_ids),
            "paper_ids": stale_ids,
            "replacement_date": stale_date,
            "expected_effect": "Freshness checks should detect more stale rows.",
        }
    )

    # Recalculate derived fields after field-level corruption.
    if "summary_chars" in corrupted.columns:
        corrupted["summary_chars"] = (
            corrupted["summary"].fillna("").astype(str).str.len()
        )

    if "age_days" in corrupted.columns:
        parsed_dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
        now = pd.Timestamp(datetime.now(UTC)).normalize()
        corrupted["age_days"] = (now - parsed_dates.dt.normalize()).dt.days

    corrupted["text_for_embedding"] = corrupted.apply(
        _rebuild_text_for_embedding,
        axis=1,
    )

    # 6. Duplicate exact rows. Keeping paper_id unchanged lets uniqueness
    # checks detect the corruption reliably.
    duplicate_count = _scenario_size(len(corrupted), 0.12)
    duplicate_rows = corrupted.iloc[:duplicate_count].copy(deep=True)
    duplicate_ids = duplicate_rows["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    scenarios.append(
        {
            "corruption_type": "duplicate_records",
            "affected_count": len(duplicate_ids),
            "paper_ids": duplicate_ids,
            "expected_effect": "Duplicate and paper_id uniqueness checks should fail.",
        }
    )

    write_json(
        output_log_path,
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "input_rows": int(len(original)),
            "output_rows": int(len(corrupted)),
            "net_row_change": int(len(corrupted) - len(original)),
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
        },
    )

    return corrupted.reset_index(drop=True)
