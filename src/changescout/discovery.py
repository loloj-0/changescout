from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

from changescout.models import DiscoveredUrlRecord, SourceConfig

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT_SECONDS = 20

EXCLUDED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".xlsm",
    ".xltx",
    ".docm",
}

def decode_response_text(response: requests.Response) -> str:
    content_type = response.headers.get("Content-Type", "").lower()

    if "charset=" in content_type:
        return response.text

    return response.content.decode("utf-8", errors="replace")


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
        },
        allow_redirects=True,
    )
    LOGGER.info(
        "Fetch response url=%s status_code=%s final_url=%s",
        url,
        response.status_code,
        response.url,
    )
    response.raise_for_status()
    return decode_response_text(response)


def extract_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for tag in soup.find_all("a"):
        href = tag.get("href")
        if href is None:
            continue

        href = href.strip()
        if not href:
            continue

        if href.startswith("#"):
            continue

        lower_href = href.lower()
        if lower_href.startswith("mailto:"):
            continue
        if lower_href.startswith("javascript:"):
            continue
        if lower_href.startswith("tel:"):
            continue

        links.append(href)

    return links


def normalize_url(raw_link: str, base_url: str) -> Optional[str]:
    try:
        absolute_url = urljoin(base_url, raw_link)
        absolute_url, _fragment = urldefrag(absolute_url)
        parsed = urlparse(absolute_url)

        if parsed.scheme not in {"http", "https"}:
            return None
        if not parsed.netloc:
            return None

        return absolute_url
    except Exception:
        return None


def normalize_urls(raw_links: Iterable[str], base_url: str) -> list[str]:
    normalized: list[str] = []

    for raw_link in raw_links:
        url = normalize_url(raw_link, base_url)
        if url is not None:
            normalized.append(url)

    return normalized


def match_include_pattern(url: str, include_patterns: Iterable[str]) -> Optional[str]:
    for pattern in include_patterns:
        if pattern in url:
            return pattern
    return None


def is_binary_asset(url: str) -> bool:
    lowered_url = url.lower()
    path = urlparse(lowered_url).path
    return any(path.endswith(ext) for ext in EXCLUDED_EXTENSIONS)


def filter_urls_by_patterns(
    urls: Iterable[str],
    include_patterns: Iterable[str],
) -> list[tuple[str, str]]:
    filtered: list[tuple[str, str]] = []

    for url in urls:
        if is_binary_asset(url):
            continue

        matched_pattern = match_include_pattern(url, include_patterns)
        if matched_pattern is not None:
            filtered.append((url, matched_pattern))

    return filtered


def deduplicate_urls(
    matched_urls: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []

    for url, matched_pattern in matched_urls:
        if url in seen:
            continue
        seen.add(url)
        unique.append((url, matched_pattern))

    return unique


def build_discovery_records(
    source: SourceConfig,
    matched_urls: Iterable[tuple[str, str]],
    discovered_at: str,
) -> list[DiscoveredUrlRecord]:
    records: list[DiscoveredUrlRecord] = []

    for url, matched_pattern in matched_urls:
        records.append(
            DiscoveredUrlRecord(
                source_id=source.source_id,
                url=url,
                discovered_at=discovered_at,
                base_url=source.base_url,
                matched_pattern=matched_pattern,
            )
        )

    return records


def discover_urls_from_source(
    source: SourceConfig,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    discovered_at: Optional[str] = None,
) -> list[DiscoveredUrlRecord]:
    if not source.active:
        LOGGER.info("Skipping inactive source %s", source.source_id)
        return []

    if source.crawl_type != "html_pattern":
        LOGGER.info(
            "Skipping source %s because crawl_type=%s is not supported",
            source.source_id,
            source.crawl_type,
        )
        return []

    if not source.include_patterns:
        raise ValueError(
            f"Source {source.source_id} requires include_patterns for html_pattern"
        )

    run_timestamp = discovered_at or datetime.now(timezone.utc).isoformat()

    LOGGER.info("Starting discovery for source_id=%s", source.source_id)

    html = fetch_html(source.base_url, timeout=timeout)
    raw_links = extract_links(html)
    normalized_urls = normalize_urls(raw_links, source.base_url)
    filtered_urls = filter_urls_by_patterns(normalized_urls, source.include_patterns)
    unique_urls = deduplicate_urls(filtered_urls)
    records = build_discovery_records(source, unique_urls, run_timestamp)

    LOGGER.info(
        (
            "Discovery finished for source_id=%s raw_links=%s "
            "normalized_urls=%s filtered_urls=%s unique_urls=%s"
        ),
        source.source_id,
        len(raw_links),
        len(normalized_urls),
        len(filtered_urls),
        len(records),
    )

    return records


def write_discovery_jsonl(
    records: Iterable[DiscoveredUrlRecord], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    LOGGER.info("Wrote discovery output to %s", output_path)