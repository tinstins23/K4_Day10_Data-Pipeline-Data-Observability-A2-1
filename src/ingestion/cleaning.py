from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """TODO(student): clean raw records thanh dataframe san sang de embed.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=timezone.utc)

    rows: list[dict] = []
    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(author) for author in record.authors if normalize_whitespace(author)]
        categories = [
            normalize_whitespace(category) for category in record.categories if normalize_whitespace(category)
        ]
        paper_id = normalize_whitespace(record.paper_id).lower()
        if not paper_id or not title or not summary:
            continue

        published = pd.to_datetime(record.published, errors="coerce", utc=True)
        if pd.isna(published):
            continue
        age_days = max(0, int((run_date - published.to_pydatetime()).days))

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories) or "unknown"
        text_for_embedding = normalize_whitespace(
            f"Title: {title}. Authors: {authors_joined}. Categories: {categories_joined}. Abstract: {summary}"
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": categories[0] if categories else "unknown",
                "published": published.date().isoformat(),
                "updated": str(record.updated or published.date().isoformat()),
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "abs_url",
                "pdf_url",
                "comment",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "age_days",
                "text_for_embedding",
            ]
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
