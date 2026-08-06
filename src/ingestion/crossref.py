from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import time
from pathlib import Path
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


_JATS_TAG_RE = re.compile(r"</?jats:[^>]+>", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_abstract(value: str) -> str:
    text = _JATS_TAG_RE.sub(" ", value)
    text = _HTML_TAG_RE.sub(" ", text)
    return normalize_whitespace(text)


def _first_title(item: dict[str, Any]) -> str:
    titles = item.get("title") or []
    if isinstance(titles, list) and titles:
        return normalize_whitespace(str(titles[0]))
    return ""


def _authors(item: dict[str, Any]) -> list[str]:
    authors: list[str] = []
    for author in item.get("author") or []:
        given = normalize_whitespace(str(author.get("given") or ""))
        family = normalize_whitespace(str(author.get("family") or ""))
        name = normalize_whitespace(f"{given} {family}")
        if not name:
            name = normalize_whitespace(str(author.get("name") or ""))
        if name:
            authors.append(name)
    return authors


def _categories(item: dict[str, Any]) -> list[str]:
    subjects = item.get("subject") or []
    return [normalize_whitespace(str(subject)) for subject in subjects if str(subject).strip()]


def _date_from_parts(container: dict[str, Any] | None) -> str:
    if not container:
        return ""
    parts = container.get("date-parts") or []
    if not parts or not parts[0]:
        return ""
    year, month, day = (list(parts[0]) + [1, 1])[:3]
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def _published_date(item: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "created"):
        value = _date_from_parts(item.get(key))
        if value:
            return value
    return ""


def _updated_date(item: dict[str, Any]) -> str:
    return _date_from_parts(item.get("deposited")) or _published_date(item)


def _pdf_url(item: dict[str, Any]) -> str:
    for link in item.get("link") or []:
        content_type = str(link.get("content-type") or "").lower()
        url = str(link.get("URL") or "")
        if "pdf" in content_type and url:
            return url
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """TODO(student): parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    message = payload.get("message") or {}
    items = message.get("items") or []
    records: list[PaperRecord] = []

    for item in items:
        doi = normalize_whitespace(str(item.get("DOI") or ""))
        title = _first_title(item)
        summary = _clean_abstract(str(item.get("abstract") or ""))
        if not doi or not title or not summary:
            continue

        authors = _authors(item)
        categories = _categories(item)
        published = _published_date(item)
        if not published:
            continue

        abs_url = normalize_whitespace(str(item.get("URL") or f"https://doi.org/{doi}"))
        records.append(
            PaperRecord(
                paper_id=doi.lower(),
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "unknown",
                published=published,
                updated=_updated_date(item) or published,
                abs_url=abs_url,
                pdf_url=_pdf_url(item),
                comment=normalize_whitespace(str(item.get("publisher") or "")),
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "mailto": "day10-lab@example.com",
    }
    url = "https://api.crossref.org/works"
    payload: dict[str, Any] | None = None
    last_error: Exception | None = None

    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=60)
            if response.status_code in {429, 503}:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:  # noqa: BLE001 - retry transient API failures
            last_error = exc
            time.sleep(2 ** attempt)

    if payload is None:
        raise RuntimeError(f"Failed to fetch Crossref data: {last_error}")

    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    payload = read_json(path)
    records: list[PaperRecord] = []
    for item in payload:
        records.append(
            PaperRecord(
                paper_id=str(item["paper_id"]),
                title=str(item["title"]),
                summary=str(item["summary"]),
                authors=list(item.get("authors") or []),
                categories=list(item.get("categories") or []),
                primary_category=str(item.get("primary_category") or "unknown"),
                published=str(item["published"]),
                updated=str(item.get("updated") or item["published"]),
                abs_url=str(item.get("abs_url") or ""),
                pdf_url=str(item.get("pdf_url") or ""),
                comment=str(item.get("comment") or ""),
            )
        )
    return records
