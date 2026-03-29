from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError(f"YAML must be a dict: {path}")

    return data


def load_scope(path: str | Path) -> ScopeConfig:
    data = load_yaml(path)

    missing = REQUIRED_SCOPE_FIELDS - data.keys()
    if missing:
        raise ValueError(f"Missing required scope fields: {sorted(missing)}")

    return ScopeConfig(
        version=data["version"],
        canton_id=data["canton_id"],
        languages=data["languages"],
        time_window_days=data["time_window_days"],
        source_registry=data["source_registry"],
        source_policy=data["source_policy"],
    )


def load_source_registry(path: str | Path) -> list[SourceConfig]:
    data = load_yaml(path)

    if "sources" not in data:
        raise ValueError("Missing 'sources' key")

    sources = []
    seen_ids = set()

    for item in data["sources"]:
        missing = REQUIRED_SOURCE_FIELDS - item.keys()
        if missing:
            raise ValueError(f"Missing fields in source: {missing}")

        if item["source_id"] in seen_ids:
            raise ValueError(f"Duplicate source_id: {item['source_id']}")
        seen_ids.add(item["source_id"])

        sources.append(
            SourceConfig(
                source_id=item["source_id"],
                name=item["name"],
                base_url=item["base_url"],
                crawl_type=item["crawl_type"],
                crawl_frequency_hours=item["crawl_frequency_hours"],
                active=item["active"],
            )
        )

    return sorted(sources, key=lambda s: s.source_id)


def resolve_active_sources(config_dir: str | Path):
    config_dir = Path(config_dir)

    scope = load_scope(config_dir / "scope.yaml")
    sources = load_source_registry(
        config_dir / "sources" / f"{scope.source_registry}.yaml"
    )

    active_sources = [s for s in sources if s.active]

    return scope, active_sources