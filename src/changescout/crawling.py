from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from changescout.io import load_discovered_url_records, write_crawl_records_jsonl
from changescout.models import CrawlRecord


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    text: str

    def __post_init__(self):
        if not isinstance(self.url, str) or not self.url:
            raise ValueError("url must be a non-empty string")

        if not isinstance(self.status_code, int):
            raise ValueError("status_code must be an integer")

        if not isinstance(self.text, str):
            raise ValueError("text must be a string")


def fetch_page(url: str, timeout_seconds: int = 10) -> FetchResult:
    if not isinstance(url, str) or not url:
        raise ValueError("url must be a non-empty string")

    if not isinstance(timeout_seconds, int):
        raise ValueError("timeout_seconds must be an integer")

    response = requests.get(
        url,
        timeout=timeout_seconds,
        allow_redirects=True,
        headers={"User-Agent": "changescout/0.1"},
    )

    return FetchResult(
        url=url,
        status_code=response.status_code,
        text=response.text,
    )


def store_html(
    base_dir: Path,
    run_id: str,
    source_id: str,
    content_hash: str,
    html: str,
) -> Path:
    if not isinstance(base_dir, Path):
        raise ValueError("base_dir must be a Path")

    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be a non-empty string")

    if not isinstance(source_id, str) or not source_id:
        raise ValueError("source_id must be a non-empty string")

    if not isinstance(content_hash, str) or not content_hash:
        raise ValueError("content_hash must be a non-empty string")

    if not isinstance(html, str):
        raise ValueError("html must be a string")

    output_dir = base_dir / run_id / source_id
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{content_hash}.html"
    file_path.write_text(html, encoding="utf-8")

    return file_path


def compute_content_hash(html: str) -> str:
    if not isinstance(html, str):
        raise ValueError("html must be a string")

    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_success_crawl_record(
    source_id: str,
    url: str,
    status_code: int,
    content_hash: str,
    html_path: Path,
    discovered_at: str | None = None,
    fetched_at: str | None = None,
) -> CrawlRecord:
    if fetched_at is None:
        fetched_at = utc_now_iso()

    return CrawlRecord(
        source_id=source_id,
        url=url,
        fetched_at=fetched_at,
        status_code=status_code,
        content_hash=content_hash,
        html_path=str(html_path),
        discovered_at=discovered_at,
    )


def build_error_crawl_record(
    source_id: str,
    url: str,
    error: str,
    discovered_at: str | None = None,
    fetched_at: str | None = None,
    status_code: int = 0,
) -> CrawlRecord:
    if fetched_at is None:
        fetched_at = utc_now_iso()

    return CrawlRecord(
        source_id=source_id,
        url=url,
        fetched_at=fetched_at,
        status_code=status_code,
        error=error,
        discovered_at=discovered_at,
    )


def log_crawl_success(record: CrawlRecord) -> None:
    logger.info(
        "crawl_success source_id=%s url=%s status_code=%s content_hash=%s html_path=%s",
        record.source_id,
        record.url,
        record.status_code,
        record.content_hash,
        record.html_path,
    )


def log_crawl_failure(record: CrawlRecord) -> None:
    logger.warning(
        "crawl_failure source_id=%s url=%s status_code=%s error=%s",
        record.source_id,
        record.url,
        record.status_code,
        record.error,
    )


def run_crawling(
    discovery_input_path: Path,
    output_jsonl_path: Path,
    html_base_dir: Path,
    run_id: str,
    timeout_seconds: int = 10,
) -> list[CrawlRecord]:
    if not isinstance(discovery_input_path, Path):
        raise ValueError("discovery_input_path must be a Path")

    if not isinstance(output_jsonl_path, Path):
        raise ValueError("output_jsonl_path must be a Path")

    if not isinstance(html_base_dir, Path):
        raise ValueError("html_base_dir must be a Path")

    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be a non-empty string")

    if not isinstance(timeout_seconds, int):
        raise ValueError("timeout_seconds must be an integer")

    discovered_records = load_discovered_url_records(discovery_input_path)
    crawl_records: list[CrawlRecord] = []

    logger.info(
        "crawl_start discovery_input=%s record_count=%s run_id=%s",
        discovery_input_path,
        len(discovered_records),
        run_id,
    )

    for discovered_record in discovered_records:
        try:
            fetch_result = fetch_page(
                url=discovered_record.url,
                timeout_seconds=timeout_seconds,
            )

            content_hash = compute_content_hash(fetch_result.text)
            html_path = store_html(
                base_dir=html_base_dir,
                run_id=run_id,
                source_id=discovered_record.source_id,
                content_hash=content_hash,
                html=fetch_result.text,
            )

            crawl_record = build_success_crawl_record(
                source_id=discovered_record.source_id,
                url=discovered_record.url,
                status_code=fetch_result.status_code,
                content_hash=content_hash,
                html_path=html_path,
                discovered_at=discovered_record.discovered_at,
            )

            log_crawl_success(crawl_record)
            crawl_records.append(crawl_record)

        except requests.RequestException as exc:
            crawl_record = build_error_crawl_record(
                source_id=discovered_record.source_id,
                url=discovered_record.url,
                error=str(exc),
                discovered_at=discovered_record.discovered_at,
            )

            log_crawl_failure(crawl_record)
            crawl_records.append(crawl_record)

    write_crawl_records_jsonl(output_jsonl_path, crawl_records)

    logger.info(
        "crawl_complete output_jsonl=%s record_count=%s run_id=%s",
        output_jsonl_path,
        len(crawl_records),
        run_id,
    )

    return crawl_records