from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from changescout.discovery import (
    build_discovery_records,
    decode_response_text,
    deduplicate_urls,
    discover_urls_from_source,
    extract_links,
    filter_urls_by_patterns,
    normalize_url,
    normalize_urls,
    write_discovery_jsonl,
)
from changescout.models import SourceConfig


def test_extract_links_ignores_invalid_and_non_navigation_links() -> None:
    html = """
    <html>
      <body>
        <a href="/project-1">Project 1</a>
        <a href="https://example.org/project-2">Project 2</a>
        <a href="">Empty</a>
        <a>No href</a>
        <a href="#section">Fragment</a>
        <a href="mailto:test@example.org">Mail</a>
        <a href="javascript:void(0)">JS</a>
      </body>
    </html>
    """

    links = extract_links(html)

    assert links == ["/project-1", "https://example.org/project-2"]


def test_normalize_url_resolves_relative_and_removes_fragment() -> None:
    url = normalize_url("/foo/bar#top", "https://www.zh.ch/de")
    assert url == "https://www.zh.ch/foo/bar"


def test_normalize_urls_discards_invalid_scheme() -> None:
    links = ["/foo", "tel:+41000000000", "javascript:void(0)"]
    urls = normalize_urls(links, "https://www.zh.ch/de")
    assert urls == ["https://www.zh.ch/foo"]


def test_filter_urls_by_patterns_keeps_only_matching_urls() -> None:
    urls = [
        "https://www.zh.ch/de/mobilitaet/strassen/projekt-a",
        "https://www.zh.ch/de/gesundheit/thema-b",
    ]

    filtered = filter_urls_by_patterns(urls, ["/mobilitaet/", "/tiefbau/"])

    assert filtered == [
        ("https://www.zh.ch/de/mobilitaet/strassen/projekt-a", "/mobilitaet/")
    ]


def test_deduplicate_urls_preserves_order() -> None:
    matched_urls = [
        ("https://www.zh.ch/de/a", "/de/"),
        ("https://www.zh.ch/de/b", "/de/"),
        ("https://www.zh.ch/de/a", "/de/"),
    ]

    unique = deduplicate_urls(matched_urls)

    assert unique == [
        ("https://www.zh.ch/de/a", "/de/"),
        ("https://www.zh.ch/de/b", "/de/"),
    ]


def test_build_records_attaches_metadata() -> None:
    source = SourceConfig(
        source_id="zh_projects",
        name="ZH Projects",
        base_url="https://www.zh.ch/de",
        crawl_type="html_pattern",
        crawl_frequency_hours=24,
        active=True,
        include_patterns=["/mobilitaet/"],
    )

    records = build_discovery_records(
        source=source,
        matched_urls=[("https://www.zh.ch/de/mobilitaet/a", "/mobilitaet/")],
        discovered_at="2026-03-29T10:00:00+00:00",
    )

    assert len(records) == 1
    assert records[0].source_id == "zh_projects"
    assert records[0].url == "https://www.zh.ch/de/mobilitaet/a"
    assert records[0].matched_pattern == "/mobilitaet/"
    assert records[0].base_url == "https://www.zh.ch/de"


def test_write_discovery_jsonl(tmp_path: Path) -> None:
    source = SourceConfig(
        source_id="zh_projects",
        name="ZH Projects",
        base_url="https://www.zh.ch/de",
        crawl_type="html_pattern",
        crawl_frequency_hours=24,
        active=True,
        include_patterns=["/mobilitaet/"],
    )

    records = build_discovery_records(
        source=source,
        matched_urls=[("https://www.zh.ch/de/mobilitaet/a", "/mobilitaet/")],
        discovered_at="2026-03-29T10:00:00+00:00",
    )

    output_path = tmp_path / "discovery.jsonl"
    write_discovery_jsonl(records, output_path)

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert '"source_id": "zh_projects"' in lines[0]

def test_decode_response_text_defaults_to_utf8_without_charset() -> None:
    response = Mock()
    response.headers = {"Content-Type": "text/html"}
    response.content = "für Zürich".encode("utf-8")
    response.text = "fÃ¼r ZÃ¼rich"

    assert decode_response_text(response) == "für Zürich"

def test_discover_urls_from_source_end_to_end_with_mocked_fetch() -> None:
    source = SourceConfig(
        source_id="zh_projects",
        name="ZH Projects",
        base_url="https://www.zh.ch/de",
        crawl_type="html_pattern",
        crawl_frequency_hours=24,
        active=True,
        include_patterns=["/mobilitaet/", "/tiefbau/"],
    )

    html = """
    <html>
      <body>
        <a href="/mobilitaet/projekt-a">Project A</a>
        <a href="/mobilitaet/projekt-a#section">Project A Fragment</a>
        <a href="https://www.zh.ch/de/tiefbau/projekt-b">Project B</a>
        <a href="/gesundheit/thema-c">Topic C</a>
        <a href="mailto:test@example.org">Mail</a>
        <a href="">Empty</a>
      </body>
    </html>
    """

    mock_response = Mock()
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.content = html.encode("utf-8")
    mock_response.text = html
    mock_response.status_code = 200
    mock_response.url = source.base_url
    mock_response.raise_for_status.return_value = None

    with patch("changescout.discovery.requests.get", return_value=mock_response) as mock_get:
        records = discover_urls_from_source(
            source=source,
            timeout=5,
            discovered_at="2026-03-29T10:00:00+00:00",
        )

    mock_get.assert_called_once()
    
    called_args, called_kwargs = mock_get.call_args

    assert called_args == ("https://www.zh.ch/de",)
    assert called_kwargs["timeout"] == 5
    assert called_kwargs["allow_redirects"] is True
    assert "headers" in called_kwargs
    assert "User-Agent" in called_kwargs["headers"]
    assert "Accept" in called_kwargs["headers"]
    assert "Accept-Language" in called_kwargs["headers"]

    assert len(records) == 2

    assert records[0].url == "https://www.zh.ch/mobilitaet/projekt-a"
    assert records[0].matched_pattern == "/mobilitaet/"

    assert records[1].url == "https://www.zh.ch/de/tiefbau/projekt-b"
    assert records[1].matched_pattern == "/tiefbau/"