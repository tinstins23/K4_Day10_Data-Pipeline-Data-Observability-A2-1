from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 503}
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.5


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


def _strip_markup(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return normalize_whitespace(without_tags)


def _first_string(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = _first_string(item)
            if text:
                return text
        return ""
    if value is None:
        return ""
    return normalize_whitespace(str(value))


def _date_parts_to_iso(container: Any) -> str:
    if not isinstance(container, dict):
        return ""
    date_parts = container.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts:
        return ""
    parts = date_parts[0]
    if not isinstance(parts, list) or not parts:
        return ""
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
    except (TypeError, ValueError):
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_authors(item: dict[str, Any]) -> list[str]:
    authors: list[str] = []
    for author in item.get("author") or []:
        if not isinstance(author, dict):
            continue
        name = normalize_whitespace(
            f"{author.get('given', '')} {author.get('family', '')}".strip()
            or str(author.get("name", "")).strip()
        )
        if name:
            authors.append(name)
    return authors


def _extract_pdf_url(item: dict[str, Any]) -> str:
    for link in item.get("link") or []:
        if not isinstance(link, dict):
            continue
        content_type = str(link.get("content-type", "")).lower()
        url = str(link.get("URL", "")).strip()
        if url and "pdf" in content_type:
            return url
    return ""


def _extract_published(item: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "created"):
        iso = _date_parts_to_iso(item.get(key))
        if iso:
            return iso
    return ""


def _extract_updated(item: dict[str, Any]) -> str:
    for key in ("indexed", "deposited", "created", "published"):
        iso = _date_parts_to_iso(item.get(key))
        if iso:
            return iso
    return ""


def _item_to_record(item: dict[str, Any]) -> PaperRecord | None:
    doi = _first_string(item.get("DOI"))
    title = _strip_markup(_first_string(item.get("title")))
    summary = _strip_markup(_first_string(item.get("abstract")))
    if not doi or not title or not summary:
        return None

    categories = [
        normalize_whitespace(str(subject))
        for subject in (item.get("subject") or [])
        if normalize_whitespace(str(subject))
    ]
    published = _extract_published(item)
    updated = _extract_updated(item) or published
    abs_url = _first_string(item.get("URL")) or f"https://doi.org/{doi}"
    comment = _first_string(item.get("container-title"))

    return PaperRecord(
        paper_id=doi,
        title=title,
        summary=summary,
        authors=_extract_authors(item),
        categories=categories,
        primary_category=categories[0] if categories else "",
        published=published,
        updated=updated,
        abs_url=abs_url,
        pdf_url=_extract_pdf_url(item),
        comment=comment,
    )


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    message = payload.get("message") or {}
    items = message.get("items") or []
    records: list[PaperRecord] = []
    seen: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        record = _item_to_record(item)
        if record is None:
            continue
        paper_id = record.paper_id.lower()
        if paper_id in seen:
            continue
        seen.add(paper_id)
        records.append(record)

    return records


def _request_with_retry(params: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "User-Agent": "day10-data-observability-lab/0.1 (mailto:student@example.com)",
        "Accept": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=60,
            )
            if response.status_code in RETRYABLE_STATUS_CODES:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    sleep_seconds = float(retry_after)
                else:
                    sleep_seconds = BASE_BACKOFF_SECONDS * (2**attempt)
                time.sleep(sleep_seconds)
                continue

            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Crossref response is not a JSON object.")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(BASE_BACKOFF_SECONDS * (2**attempt))

    raise RuntimeError(f"Failed to fetch Crossref works after {MAX_RETRIES} retries.") from last_error


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    payload = _request_with_retry(params)

    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of records in {path}")

    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            PaperRecord(
                paper_id=str(item.get("paper_id", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
                authors=[str(a) for a in (item.get("authors") or [])],
                categories=[str(c) for c in (item.get("categories") or [])],
                primary_category=str(item.get("primary_category", "")),
                published=str(item.get("published", "")),
                updated=str(item.get("updated", "")),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records
