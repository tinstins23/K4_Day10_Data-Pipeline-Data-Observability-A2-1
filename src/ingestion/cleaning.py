from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date(value: str) -> datetime | None:
    text = normalize_whitespace(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _normalize_authors(authors: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for author in authors:
        name = normalize_whitespace(author)
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return cleaned


def _normalize_categories(categories: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for category in categories:
        name = normalize_whitespace(category)
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return cleaned


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    run_day = run_date.replace(tzinfo=None).date()
    rows: list[dict] = []

    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = _normalize_authors(record.authors)
        categories = _normalize_categories(record.categories)
        published_dt = _parse_date(record.published)
        updated_dt = _parse_date(record.updated) or published_dt

        if not record.paper_id or not title or not summary or published_dt is None:
            continue

        age_days = (run_day - published_dt.date()).days
        if age_days < 0:
            age_days = 0

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        primary_category = categories[0] if categories else normalize_whitespace(record.primary_category)
        text_for_embedding = normalize_whitespace(
            f"Title: {title}. Authors: {authors_joined}. "
            f"Categories: {categories_joined}. Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": normalize_whitespace(record.paper_id),
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_dt.date().isoformat(),
                "updated": updated_dt.date().isoformat() if updated_dt else "",
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "authors_joined",
                "categories",
                "categories_joined",
                "primary_category",
                "published",
                "updated",
                "age_days",
                "summary_chars",
                "text_for_embedding",
                "abs_url",
                "pdf_url",
                "comment",
            ]
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["summary_chars"] >= 40].copy()
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
