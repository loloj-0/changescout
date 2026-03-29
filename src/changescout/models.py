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


@dataclass(frozen=True)
class DiscoveredUrlRecord:
    source_id: str
    url: str
    discovered_at: str
    base_url: Optional[str] = None
    matched_pattern: Optional[str] = None