from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    name: str
    base_url: str
    crawl_type: str
    crawl_frequency_hours: int
    active: bool
    include_patterns: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.source_id, str) or not self.source_id:
            raise ValueError("source_id must be a non-empty string")

        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")

        if not isinstance(self.base_url, str) or not self.base_url:
            raise ValueError("base_url must be a non-empty string")

        if not isinstance(self.crawl_type, str) or not self.crawl_type:
            raise ValueError("crawl_type must be a non-empty string")

        if not isinstance(self.crawl_frequency_hours, int):
            raise ValueError("crawl_frequency_hours must be an integer")

        if not isinstance(self.active, bool):
            raise ValueError("active must be a boolean")

        if not isinstance(self.include_patterns, list):
            raise ValueError("include_patterns must be a list")

        if self.crawl_type == "html_pattern" and not self.include_patterns:
            raise ValueError("include_patterns required for html_pattern sources")


@dataclass(frozen=True)
class DiscoveredUrlRecord:
    source_id: str
    url: str
    discovered_at: str
    base_url: Optional[str] = None
    matched_pattern: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.source_id, str) or not self.source_id:
            raise ValueError("source_id must be a non-empty string")

        if not isinstance(self.url, str) or not self.url:
            raise ValueError("url must be a non-empty string")

        if not isinstance(self.discovered_at, str) or not self.discovered_at:
            raise ValueError("discovered_at must be a non-empty string timestamp")

        if self.base_url is not None and not isinstance(self.base_url, str):
            raise ValueError("base_url must be a string if provided")

        if self.matched_pattern is not None and not isinstance(self.matched_pattern, str):
            raise ValueError("matched_pattern must be a string if provided")


@dataclass(frozen=True)
class CrawlRecord:
    source_id: str
    url: str
    fetched_at: str
    status_code: int
    content_hash: Optional[str] = None
    html_path: Optional[str] = None
    error: Optional[str] = None
    discovered_at: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.source_id, str) or not self.source_id:
            raise ValueError("source_id must be a non-empty string")

        if not isinstance(self.url, str) or not self.url:
            raise ValueError("url must be a non-empty string")

        if not isinstance(self.fetched_at, str) or not self.fetched_at:
            raise ValueError("fetched_at must be a non-empty string timestamp")

        if not isinstance(self.status_code, int):
            raise ValueError("status_code must be an integer")

        if self.content_hash is not None and not isinstance(self.content_hash, str):
            raise ValueError("content_hash must be a string if provided")

        if self.html_path is not None and not isinstance(self.html_path, str):
            raise ValueError("html_path must be a string if provided")

        if self.error is not None and not isinstance(self.error, str):
            raise ValueError("error must be a string if provided")

        if self.discovered_at is not None and not isinstance(self.discovered_at, str):
            raise ValueError("discovered_at must be a string if provided")

        has_success_payload = self.content_hash is not None or self.html_path is not None

        if self.error is not None and has_success_payload:
            raise ValueError("error records must not contain content_hash or html_path")

        if self.error is None:
            if self.content_hash is None:
                raise ValueError("successful crawl records must contain content_hash")
            if self.html_path is None:
                raise ValueError("successful crawl records must contain html_path")