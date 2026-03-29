from pathlib import Path

import pytest

from changescout.config import (
    SourceConfig,
    ScopeConfig,
    load_scope,
    load_source_registry,
    load_yaml,
    resolve_active_sources,
)


def test_load_yaml_returns_dict(tmp_path: Path):
    file_path = tmp_path / "sample.yaml"
    file_path.write_text("key: value\n")

    data = load_yaml(file_path)

    assert data == {"key": "value"}


def test_load_scope_valid(tmp_path: Path):
    file_path = tmp_path / "scope.yaml"
    file_path.write_text(
        """version: 1
canton_id: uri
languages:
  - de
time_window_days: 30
source_registry: uri
source_policy: official_canton_only
"""
    )

    scope = load_scope(file_path)

    assert isinstance(scope, ScopeConfig)
    assert scope.canton_id == "uri"


def test_load_scope_missing_field(tmp_path: Path):
    file_path = tmp_path / "scope.yaml"
    file_path.write_text(
        """version: 1
canton_id: uri
"""
    )

    with pytest.raises(ValueError):
        load_scope(file_path)


def test_load_source_registry(tmp_path: Path):
    file_path = tmp_path / "uri.yaml"
    file_path.write_text(
        """version: 1
sources:
  - source_id: b
    name: B
    base_url: https://b.ch
    crawl_type: html
    crawl_frequency_hours: 24
    active: true
  - source_id: a
    name: A
    base_url: https://a.ch
    crawl_type: html
    crawl_frequency_hours: 24
    active: false
"""
    )

    sources = load_source_registry(file_path)

    assert [s.source_id for s in sources] == ["a", "b"]


def test_resolve_active_sources(tmp_path: Path):
    config_dir = tmp_path / "config"
    sources_dir = config_dir / "sources"
    sources_dir.mkdir(parents=True)

    (config_dir / "scope.yaml").write_text(
        """version: 1
canton_id: uri
languages:
  - de
time_window_days: 30
source_registry: uri
source_policy: official_canton_only
"""
    )

    (sources_dir / "uri.yaml").write_text(
        """version: 1
sources:
  - source_id: b
    name: B
    base_url: https://b.ch
    crawl_type: html
    crawl_frequency_hours: 24
    active: true
  - source_id: a
    name: A
    base_url: https://a.ch
    crawl_type: html
    crawl_frequency_hours: 24
    active: false
"""
    )

    scope, active_sources = resolve_active_sources(config_dir)

    assert scope.canton_id == "uri"
    assert [s.source_id for s in active_sources] == ["b"]