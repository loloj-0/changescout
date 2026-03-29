from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


ALLOWED_CRAWL_TYPES = {"html_list", "html_pattern"}

REQUIRED_SCOPE_FIELDS = {
    "version",
    "canton_id",
    "languages",
    "time_window_days",
    "source_registry",
    "source_policy",
}

REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "name",
    "base_url",
    "crawl_type",
    "crawl_frequency_hours",
    "active",
}


@dataclass(frozen=True)
class ScopeConfig:
    version: int
    canton_id: str
    languages: list[str]
    time_window_days: int
    source_registry: str
    source_policy: str


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    name: str
    base_url: str
    crawl_type: str
    crawl_frequency_hours: int
    active: bool
    include_patterns: list[str] | None = None


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError(f"YAML top level must be a mapping: {path}")

    return data


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_scope(path: str | Path) -> ScopeConfig:
    data = load_yaml(path)

    missing = REQUIRED_SCOPE_FIELDS - data.keys()
    if missing:
        raise ValueError(f"Missing required scope fields: {sorted(missing)}")

    version = data["version"]
    canton_id = data["canton_id"]
    languages = data["languages"]
    time_window_days = data["time_window_days"]
    source_registry = data["source_registry"]
    source_policy = data["source_policy"]

    if not isinstance(version, int) or version < 1:
        raise ValueError("Scope field 'version' must be a positive integer")

    if not _is_non_empty_string(canton_id):
        raise ValueError("Scope field 'canton_id' must be a non-empty string")

    if not isinstance(languages, list) or not languages:
        raise ValueError("Scope field 'languages' must be a non-empty list")

    if not all(_is_non_empty_string(lang) for lang in languages):
        raise ValueError("All scope languages must be non-empty strings")

    if not isinstance(time_window_days, int) or time_window_days < 1:
        raise ValueError("Scope field 'time_window_days' must be a positive integer")

    if not _is_non_empty_string(source_registry):
        raise ValueError("Scope field 'source_registry' must be a non-empty string")

    if not _is_non_empty_string(source_policy):
        raise ValueError("Scope field 'source_policy' must be a non-empty string")

    return ScopeConfig(
        version=version,
        canton_id=canton_id,
        languages=languages,
        time_window_days=time_window_days,
        source_registry=source_registry,
        source_policy=source_policy,
    )


def load_source_registry(path: str | Path) -> list[SourceConfig]:
    data = load_yaml(path)

    if "sources" not in data:
        raise ValueError("Missing 'sources' key in source registry")

    if not isinstance(data["sources"], list):
        raise ValueError("Source registry field 'sources' must be a list")

    sources: list[SourceConfig] = []
    seen_ids: set[str] = set()

    for item in data["sources"]:
        if not isinstance(item, dict):
            raise ValueError("Each source entry must be a mapping")

        missing = REQUIRED_SOURCE_FIELDS - item.keys()
        if missing:
            raise ValueError(f"Missing fields in source: {sorted(missing)}")

        source_id = item["source_id"]
        name = item["name"]
        base_url = item["base_url"]
        crawl_type = item["crawl_type"]
        crawl_frequency_hours = item["crawl_frequency_hours"]
        active = item["active"]
        include_patterns = item.get("include_patterns")

        if not _is_non_empty_string(source_id):
            raise ValueError("Source field 'source_id' must be a non-empty string")

        if source_id in seen_ids:
            raise ValueError(f"Duplicate source_id: {source_id}")
        seen_ids.add(source_id)

        if not _is_non_empty_string(name):
            raise ValueError(f"Source '{source_id}' has invalid 'name'")

        if not _is_non_empty_string(base_url) or not _is_valid_http_url(base_url):
            raise ValueError(f"Source '{source_id}' has invalid 'base_url'")

        if crawl_type not in ALLOWED_CRAWL_TYPES:
            raise ValueError(
                f"Source '{source_id}' has invalid 'crawl_type': {crawl_type}"
            )

        if not isinstance(crawl_frequency_hours, int) or crawl_frequency_hours < 1:
            raise ValueError(
                f"Source '{source_id}' has invalid 'crawl_frequency_hours'"
            )

        if not isinstance(active, bool):
            raise ValueError(f"Source '{source_id}' has invalid 'active' flag")

        if crawl_type == "html_pattern":
            if include_patterns is None:
                raise ValueError(
                    f"Source '{source_id}' requires 'include_patterns' for html_pattern"
                )
            if not isinstance(include_patterns, list) or not include_patterns:
                raise ValueError(
                    f"Source '{source_id}' must define a non-empty list of include_patterns"
                )
            if not all(_is_non_empty_string(p) for p in include_patterns):
                raise ValueError(
                    f"Source '{source_id}' has invalid include_patterns values"
                )
        else:
            if include_patterns is not None:
                raise ValueError(
                    f"Source '{source_id}' must not define include_patterns for crawl_type '{crawl_type}'"
                )

        sources.append(
            SourceConfig(
                source_id=source_id,
                name=name,
                base_url=base_url,
                crawl_type=crawl_type,
                crawl_frequency_hours=crawl_frequency_hours,
                active=active,
                include_patterns=include_patterns,
            )
        )

    return sorted(sources, key=lambda s: s.source_id)


def resolve_active_sources(config_dir: str | Path) -> tuple[ScopeConfig, list[SourceConfig]]:
    config_dir = Path(config_dir)

    scope = load_scope(config_dir / "scope.yaml")
    sources = load_source_registry(
        config_dir / "sources" / f"{scope.source_registry}.yaml"
    )

    active_sources = [source for source in sources if source.active]

    return scope, active_sources