from pathlib import Path

import pytest

from changescout.config import (
    ScopeConfig,
    load_scope,
    load_source_registry,
    load_yaml,
    resolve_active_sources,
)


def test_load_yaml_returns_dict(tmp_path: Path):
    file_path = tmp_path / "sample.yaml"
    file_path.write_text("key: value\n", encoding="utf-8")

    data = load_yaml(file_path)

    assert data == {"key": "value"}


def test_load_scope_valid(tmp_path: Path):
    file_path = tmp_path / "scope.yaml"
    file_path.write_text(
        """version: 1
canton_id: zh
languages:
  - de
time_window_days: 30
source_registry: zh
source_policy: official_canton_only
""",
        encoding="utf-8",
    )

    scope = load_scope(file_path)

    assert isinstance(scope, ScopeConfig)
    assert scope.canton_id == "zh"
    assert scope.languages == ["de"]


def test_load_scope_missing_field(tmp_path: Path):
    file_path = tmp_path / "scope.yaml"
    file_path.write_text(
        """version: 1
canton_id: zh
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required scope fields"):
        load_scope(file_path)


def test_load_scope_invalid_languages(tmp_path: Path):
    file_path = tmp_path / "scope.yaml"
    file_path.write_text(
        """version: 1
canton_id: zh
languages: []
time_window_days: 30
source_registry: zh
source_policy: official_canton_only
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="languages"):
        load_scope(file_path)


def test_load_source_registry_valid_html_pattern(tmp_path: Path):
    file_path = tmp_path / "zh.yaml"
    file_path.write_text(
        """version: 1
sources:
  - source_id: b
    name: B
    base_url: https://example.ch/root
    crawl_type: html_pattern
    include_patterns:
      - /foo/
      - /bar/
    crawl_frequency_hours: 24
    active: true
  - source_id: a
    name: A
    base_url: https://example.ch/list
    crawl_type: html_list
    crawl_frequency_hours: 24
    active: false
""",
        encoding="utf-8",
    )

    sources = load_source_registry(file_path)

    assert [s.source_id for s in sources] == ["a", "b"]
    assert sources[1].include_patterns == ["/foo/", "/bar/"]


def test_load_source_registry_duplicate_source_id(tmp_path: Path):
    file_path = tmp_path / "zh.yaml"
    file_path.write_text(
        """version: 1
sources:
  - source_id: dup
    name: A
    base_url: https://a.ch
    crawl_type: html_list
    crawl_frequency_hours: 24
    active: true
  - source_id: dup
    name: B
    base_url: https://b.ch
    crawl_type: html_list
    crawl_frequency_hours: 24
    active: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate source_id"):
        load_source_registry(file_path)


def test_load_source_registry_invalid_url(tmp_path: Path):
    file_path = tmp_path / "zh.yaml"
    file_path.write_text(
        """version: 1
sources:
  - source_id: a
    name: A
    base_url: not_a_url
    crawl_type: html_list
    crawl_frequency_hours: 24
    active: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid 'base_url'"):
        load_source_registry(file_path)


def test_load_source_registry_missing_include_patterns_for_html_pattern(tmp_path: Path):
    file_path = tmp_path / "zh.yaml"
    file_path.write_text(
        """version: 1
sources:
  - source_id: a
    name: A
    base_url: https://example.ch/root
    crawl_type: html_pattern
    crawl_frequency_hours: 24
    active: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires 'include_patterns'"):
        load_source_registry(file_path)


def test_load_source_registry_invalid_crawl_type(tmp_path: Path):
    file_path = tmp_path / "zh.yaml"
    file_path.write_text(
        """version: 1
sources:
  - source_id: a
    name: A
    base_url: https://example.ch/root
    crawl_type: html
    crawl_frequency_hours: 24
    active: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid 'crawl_type'"):
        load_source_registry(file_path)


def test_resolve_active_sources(tmp_path: Path):
    config_dir = tmp_path / "config"
    sources_dir = config_dir / "sources"
    sources_dir.mkdir(parents=True)

    (config_dir / "scope.yaml").write_text(
        """version: 1
canton_id: zh
languages:
  - de
time_window_days: 30
source_registry: zh
source_policy: official_canton_only
""",
        encoding="utf-8",
    )

    (sources_dir / "zh.yaml").write_text(
        """version: 1
sources:
  - source_id: b
    name: B
    base_url: https://example.ch/root
    crawl_type: html_pattern
    include_patterns:
      - /foo/
    crawl_frequency_hours: 24
    active: true
  - source_id: a
    name: A
    base_url: https://example.ch/list
    crawl_type: html_list
    crawl_frequency_hours: 24
    active: false
""",
        encoding="utf-8",
    )

    scope, active_sources = resolve_active_sources(config_dir)

    assert scope.canton_id == "zh"
    assert [s.source_id for s in active_sources] == ["b"]
    assert active_sources[0].crawl_type == "html_pattern"