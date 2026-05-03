from pathlib import Path
from unittest.mock import patch

import pytest

from changescout.crawling import (
    FetchResult,
    build_error_crawl_record,
    build_success_crawl_record,
    compute_content_hash,
    decode_response_text,
    run_crawling,
    store_html,
)
from changescout.io import load_discovered_url_records
from changescout.models import DiscoveredUrlRecord


def test_load_discovered_url_records_valid(tmp_path: Path) -> None:
    input_path = tmp_path / "discovery.jsonl"
    input_path.write_text(
        '{"source_id":"zh_tiefbau","url":"https://example.org/a","discovered_at":"2026-04-22T10:00:00Z"}\n',
        encoding="utf-8",
    )

    records = load_discovered_url_records(input_path)

    assert len(records) == 1
    assert records[0] == DiscoveredUrlRecord(
        source_id="zh_tiefbau",
        url="https://example.org/a",
        discovered_at="2026-04-22T10:00:00Z",
    )


def test_load_discovered_url_records_invalid_missing_field(tmp_path: Path) -> None:
    input_path = tmp_path / "invalid.jsonl"
    input_path.write_text(
        '{"source_id":"zh_tiefbau","url":"https://example.org/a"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid discovery record shape"):
        load_discovered_url_records(input_path)


def test_compute_content_hash_is_stable() -> None:
    h1 = compute_content_hash("<html>a</html>")
    h2 = compute_content_hash("<html>a</html>")
    h3 = compute_content_hash("<html>b</html>")

    assert h1 == h2
    assert h1 != h3

def test_decode_response_text_defaults_to_utf8_without_charset() -> None:
    class DummyResponse:
        headers = {"Content-Type": "text/html"}
        content = "für Zürich".encode("utf-8")
        text = "fÃ¼r ZÃ¼rich"

    assert decode_response_text(DummyResponse()) == "für Zürich"

def test_store_html_writes_expected_file(tmp_path: Path) -> None:
    html_path = store_html(
        base_dir=tmp_path,
        run_id="test_run",
        source_id="zh_tiefbau",
        content_hash="abc123",
        html="<html>test</html>",
    )

    assert html_path == tmp_path / "test_run" / "zh_tiefbau" / "abc123.html"
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8") == "<html>test</html>"


def test_store_html_allows_empty_body(tmp_path: Path) -> None:
    html_path = store_html(
        base_dir=tmp_path,
        run_id="test_run_empty",
        source_id="zh_tiefbau",
        content_hash="empty123",
        html="",
    )

    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8") == ""


def test_build_crawl_records_support_success_and_error() -> None:
    success = build_success_crawl_record(
        source_id="zh_tiefbau",
        url="https://example.org/a",
        status_code=200,
        content_hash="abc123",
        html_path=Path("data/crawling/test_run/zh_tiefbau/abc123.html"),
        discovered_at="2026-04-22T10:00:00Z",
        fetched_at="2026-04-22T11:00:00Z",
    )

    error = build_error_crawl_record(
        source_id="zh_tiefbau",
        url="https://example.org/b",
        error="timeout",
        discovered_at="2026-04-22T10:05:00Z",
        fetched_at="2026-04-22T11:05:00Z",
    )

    assert success.source_id == "zh_tiefbau"
    assert success.status_code == 200
    assert success.content_hash == "abc123"
    assert success.html_path == "data/crawling/test_run/zh_tiefbau/abc123.html"
    assert success.error is None

    assert error.source_id == "zh_tiefbau"
    assert error.status_code == 0
    assert error.content_hash is None
    assert error.html_path is None
    assert error.error == "timeout"


def test_run_crawling_integration(tmp_path: Path) -> None:
    import requests
    
    discovery_input_path = tmp_path / "discovery.jsonl"
    discovery_input_path.write_text(
        (
            '{"source_id":"zh_tiefbau","url":"https://example.org","discovered_at":"2026-04-22T10:00:00Z"}\n'
            '{"source_id":"zh_tiefbau","url":"https://does-not-exist.invalid","discovered_at":"2026-04-22T10:05:00Z"}\n'
        ),
        encoding="utf-8",
    )

    output_jsonl_path = tmp_path / "output.jsonl"
    html_base_dir = tmp_path / "html"

    def fake_fetch_page(url: str, timeout_seconds: int = 10) -> FetchResult:
        if url == "https://does-not-exist.invalid":
            raise requests.RequestException("mocked fetch failure")

        return FetchResult(
            url=url,
            status_code=200,
            text="<html>mocked page</html>",
        )

    with patch("changescout.crawling.fetch_page", side_effect=fake_fetch_page):
        records = run_crawling(
            discovery_input_path=discovery_input_path,
            output_jsonl_path=output_jsonl_path,
            html_base_dir=html_base_dir,
            run_id="test_run_full",
            timeout_seconds=10,
        )

    assert len(records) == 2

    success_records = [record for record in records if record.error is None]
    error_records = [record for record in records if record.error is not None]

    assert len(success_records) == 1
    assert len(error_records) == 1

    success = success_records[0]
    error = error_records[0]

    assert success.status_code == 200
    assert success.content_hash is not None
    assert success.html_path is not None

    assert error.status_code == 0
    assert error.content_hash is None
    assert error.html_path is None
    assert error.error is not None

    assert output_jsonl_path.exists()

    lines = output_jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    stored_html_files = list((html_base_dir / "test_run_full" / "zh_tiefbau").glob("*.html"))
    assert len(stored_html_files) == 1