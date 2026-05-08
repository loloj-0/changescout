from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from changescout.enrichment.lead_enrichment import (
    build_geoadmin_report,
    flatten_geoadmin_hints,
    run_local_lead_location_hinting,
    write_geoadmin_failure_report,
)


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_flatten_geoadmin_hints_extracts_names_origins_and_queries():
    record = {
        "geoadmin_location_hints": [
            {
                "name": "Bülach (ZH)",
                "origin": "gazetteer",
                "query": "bülach",
            },
            {
                "name": "Rorbas (ZH)",
                "origin": "gg25",
                "query": "rorbas",
            },
        ]
    }

    flattened = flatten_geoadmin_hints(record)

    assert flattened["geoadmin_location_hint_names"] == "Bülach (ZH); Rorbas (ZH)"
    assert flattened["geoadmin_location_origins"] == "gazetteer; gg25"
    assert flattened["geoadmin_location_queries"] == "bülach; rorbas"
    assert flattened["geoadmin_top_location_name"] == "Bülach (ZH)"


def test_build_geoadmin_report_counts_records_and_hints():
    records = [
        {
            "geoadmin_location_hint_count": 2,
            "geoadmin_query_count": 1,
            "geoadmin_cache_hits": 1,
            "geoadmin_cache_misses": 0,
            "geoadmin_location_hints": [
                {"origin": "gazetteer"},
                {"origin": "gg25"},
            ],
        },
        {
            "geoadmin_location_hint_count": 0,
            "geoadmin_query_count": 1,
            "geoadmin_cache_hits": 0,
            "geoadmin_cache_misses": 1,
            "geoadmin_location_hints": [],
        },
    ]

    report = build_geoadmin_report(records)

    assert report["total_records"] == 2
    assert report["records_with_geoadmin_hints"] == 1
    assert report["records_without_geoadmin_hints"] == 1
    assert report["total_geoadmin_hints"] == 2
    assert report["total_geoadmin_queries"] == 2
    assert report["total_cache_hits"] == 1
    assert report["total_cache_misses"] == 1
    assert report["origin_counts"] == {"gazetteer": 1, "gg25": 1}


def test_write_geoadmin_failure_report_is_non_blocking(tmp_path: Path):
    report_path = tmp_path / "reports" / "geoadmin_location_hinting_report.json"

    report = write_geoadmin_failure_report(
        report_output_path=report_path,
        error="network failed",
    )

    assert report["status"] == "failed_non_blocking"
    assert report["error"] == "network failed"
    assert report_path.exists()

    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert written["status"] == "failed_non_blocking"


def test_local_location_hinting_uses_explicit_scoped_paths(tmp_path: Path):
    input_path = tmp_path / "run" / "leads.jsonl"
    reference_path = tmp_path / "reference" / "location_hints_reference.csv"
    output_jsonl = tmp_path / "run" / "leads_with_locations.jsonl"
    output_csv = tmp_path / "run" / "leads_with_locations.csv"
    report_path = tmp_path / "run" / "reports" / "location_hinting_report.json"

    write_jsonl(
        input_path,
        [
            {
                "title": "Strassenprojekt Bülach",
                "url": "https://example.test/buelach",
                "source_id": "test",
                "text_preview": "Projekt in Bülach.",
            }
        ],
    )

    reference_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "name": "Bülach",
                "hint_type": "municipality",
                "canton": "ZH",
                "source": "test",
                "priority": 100,
            }
        ]
    ).to_csv(reference_path, index=False, encoding="utf-8")

    report = run_local_lead_location_hinting(
        input_jsonl_path=input_path,
        reference_path=reference_path,
        output_jsonl_path=output_jsonl,
        output_csv_path=output_csv,
        report_output_path=report_path,
    )

    assert output_jsonl.exists()
    assert output_csv.exists()
    assert report_path.exists()
    assert report["total_records"] == 1


def test_local_location_hinting_missing_reference_fails_explicitly(tmp_path: Path):
    input_path = tmp_path / "run" / "leads.jsonl"
    missing_reference = tmp_path / "missing" / "location_hints_reference.csv"

    write_jsonl(
        input_path,
        [
            {
                "title": "Strassenprojekt Bülach",
                "url": "https://example.test/buelach",
                "source_id": "test",
                "text_preview": "Projekt in Bülach.",
            }
        ],
    )

    with pytest.raises(FileNotFoundError):
        run_local_lead_location_hinting(
            input_jsonl_path=input_path,
            reference_path=missing_reference,
            output_jsonl_path=tmp_path / "out.jsonl",
            output_csv_path=tmp_path / "out.csv",
            report_output_path=tmp_path / "report.json",
        )
