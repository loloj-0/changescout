from pathlib import Path

import pandas as pd
import pytest

from changescout.geography import (
    build_location_hinting_report,
    enrich_records_with_location_hints,
    find_location_hints_for_document,
    flatten_location_hints,
    load_location_reference,
)


def test_load_location_reference_requires_columns(tmp_path: Path) -> None:
    path = tmp_path / "locations.csv"
    pd.DataFrame(
        [
            {
                "name": "Suhr",
                "hint_type": "municipality",
                "canton": "AG",
            }
        ]
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing reference columns"):
        load_location_reference(path)


def test_find_location_hints_matches_title_and_clean_text() -> None:
    reference = pd.DataFrame(
        [
            {
                "name": "Suhr",
                "hint_type": "municipality",
                "canton": "AG",
                "source": "bfs_municipalities",
                "priority": 100,
            },
            {
                "name": "Aarau",
                "hint_type": "municipality",
                "canton": "AG",
                "source": "bfs_municipalities",
                "priority": 100,
            },
        ]
    )

    document = {
        "title": "VERAS Raum Suhr",
        "clean_text": "Das Projekt betrifft Suhr und Aarau.",
    }

    hints = find_location_hints_for_document(document, reference)

    assert len(hints) == 2

    suhr = next(hint for hint in hints if hint["name"] == "Suhr")
    aarau = next(hint for hint in hints if hint["name"] == "Aarau")

    assert suhr["matched_fields"] == ["title", "clean_text"]
    assert suhr["match_count"] == 2
    assert aarau["matched_fields"] == ["clean_text"]
    assert aarau["match_count"] == 1


def test_find_location_hints_does_not_match_inside_longer_words() -> None:
    reference = pd.DataFrame(
        [
            {
                "name": "Bern",
                "hint_type": "municipality",
                "canton": "BE",
                "source": "bfs_municipalities",
                "priority": 100,
            }
        ]
    )

    document = {
        "title": "Berner Oberland",
        "clean_text": "Die Region ist nicht die Gemeinde Bern.",
    }

    hints = find_location_hints_for_document(document, reference)

    assert len(hints) == 1
    assert hints[0]["name"] == "Bern"
    assert hints[0]["matched_fields"] == ["clean_text"]


def test_find_location_hints_ignores_short_names_by_default() -> None:
    reference = pd.DataFrame(
        [
            {
                "name": "Au",
                "hint_type": "municipality",
                "canton": "SG",
                "source": "bfs_municipalities",
                "priority": 100,
            }
        ]
    )

    document = {
        "title": "Au",
        "clean_text": "Projekt in Au.",
    }

    hints = find_location_hints_for_document(document, reference)

    assert hints == []


def test_flatten_location_hints_creates_csv_fields() -> None:
    hints = [
        {
            "hint_type": "municipality",
            "name": "Suhr",
            "canton": "AG",
            "source": "bfs_municipalities",
            "matched_fields": ["title"],
            "match_count": 1,
            "priority": 100,
        },
        {
            "hint_type": "geographic_name",
            "name": "Aarebrücke",
            "canton": "AG",
            "source": "swissnames3d",
            "matched_fields": ["clean_text"],
            "match_count": 1,
            "priority": 60,
        },
    ]

    result = flatten_location_hints(hints)

    assert result["location_hint_count"] == 2
    assert result["location_hint_names"] == "Suhr; Aarebrücke"
    assert result["location_hint_types"] == "geographic_name; municipality"
    assert result["municipality_hints"] == "Suhr"
    assert result["geographic_name_hints"] == "Aarebrücke"


def test_enrich_records_with_location_hints_preserves_records() -> None:
    reference = pd.DataFrame(
        [
            {
                "name": "Suhr",
                "hint_type": "municipality",
                "canton": "AG",
                "source": "bfs_municipalities",
                "priority": 100,
            }
        ]
    )

    records = [
        {
            "document_id": "doc-1",
            "title": "Projekt Suhr",
            "clean_text": "Text",
        }
    ]

    enriched = enrich_records_with_location_hints(records, reference)

    assert enriched[0]["document_id"] == "doc-1"
    assert enriched[0]["location_hint_count"] == 1
    assert enriched[0]["municipality_hints"] == "Suhr"


def test_build_location_hinting_report_counts_hint_types() -> None:
    records = [
        {
            "location_hint_count": 1,
            "location_hints": [
                {
                    "hint_type": "municipality",
                    "name": "Suhr",
                }
            ],
        },
        {
            "location_hint_count": 0,
            "location_hints": [],
        },
    ]

    report = build_location_hinting_report(records)

    assert report["total_records"] == 2
    assert report["records_with_hints"] == 1
    assert report["records_without_hints"] == 1
    assert report["total_hints"] == 1
    assert report["hint_type_counts"] == {"municipality": 1}