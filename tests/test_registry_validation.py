from __future__ import annotations

from pathlib import Path

from changescout.validation.registry_validation import validate_registry_file


def write_registry(config_dir: Path, name: str, content: str) -> None:
    path = config_dir / "sources" / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validate_registry_accepts_valid_html_pattern_source(tmp_path: Path):
    write_registry(
        tmp_path,
        "xx",
        """
version: 1
sources:
  - source_id: "xx_projects"
    name: "XX Projects"
    base_url: "https://example.test/projects.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
    include_patterns:
      - "/projects/"
""",
    )

    report = validate_registry_file(tmp_path, "xx")

    assert report["valid"] is True
    assert report["error_count"] == 0
    assert report["source_count"] == 1
    assert report["active_source_count"] == 1


def test_validate_registry_rejects_missing_registry_file(tmp_path: Path):
    report = validate_registry_file(tmp_path, "missing")

    assert report["valid"] is False
    assert report["error_count"] == 1
    assert report["issues"][0]["code"] == "registry_file_missing"


def test_validate_registry_detects_duplicate_source_id(tmp_path: Path):
    write_registry(
        tmp_path,
        "xx",
        """
version: 1
sources:
  - source_id: "duplicate"
    name: "Source A"
    base_url: "https://example.test/a.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
    include_patterns:
      - "/a/"
  - source_id: "duplicate"
    name: "Source B"
    base_url: "https://example.test/b.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
    include_patterns:
      - "/b/"
""",
    )

    report = validate_registry_file(tmp_path, "xx")

    assert report["valid"] is False
    assert any(issue["code"] == "duplicate_source_id" for issue in report["issues"])


def test_validate_registry_rejects_html_pattern_without_include_patterns(tmp_path: Path):
    write_registry(
        tmp_path,
        "xx",
        """
version: 1
sources:
  - source_id: "xx_projects"
    name: "XX Projects"
    base_url: "https://example.test/projects.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
""",
    )

    report = validate_registry_file(tmp_path, "xx")

    assert report["valid"] is False
    assert any(issue["code"] == "missing_include_patterns" for issue in report["issues"])


def test_validate_registry_rejects_invalid_base_url(tmp_path: Path):
    write_registry(
        tmp_path,
        "xx",
        """
version: 1
sources:
  - source_id: "xx_projects"
    name: "XX Projects"
    base_url: "not-a-url"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
    include_patterns:
      - "/projects/"
""",
    )

    report = validate_registry_file(tmp_path, "xx")

    assert report["valid"] is False
    assert any(issue["code"] == "invalid_base_url" for issue in report["issues"])


def test_validate_registry_warns_for_broad_include_pattern(tmp_path: Path):
    write_registry(
        tmp_path,
        "xx",
        """
version: 1
sources:
  - source_id: "xx_projects"
    name: "XX Projects"
    base_url: "https://example.test/projects.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
    include_patterns:
      - "/de/"
""",
    )

    report = validate_registry_file(tmp_path, "xx")

    assert report["valid"] is True
    assert report["warning_count"] >= 1
    assert any(issue["code"] == "broad_include_pattern" for issue in report["issues"])


def test_validate_registry_rejects_no_active_sources(tmp_path: Path):
    write_registry(
        tmp_path,
        "xx",
        """
version: 1
sources:
  - source_id: "xx_projects"
    name: "XX Projects"
    base_url: "https://example.test/projects.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: false
    include_patterns:
      - "/projects/"
""",
    )

    report = validate_registry_file(tmp_path, "xx")

    assert report["valid"] is False
    assert any(issue["code"] == "no_active_sources" for issue in report["issues"])
