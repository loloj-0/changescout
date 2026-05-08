from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from changescout.review.review_export import run_review_export


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_review_export_uses_best_available_geoadmin_file(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "review_test"

    write_jsonl(
        run_dir / "leads.jsonl",
        [
            {
                "rank": 1,
                "title": "Base lead",
                "url": "https://example.test/base",
                "source_id": "test",
                "thematic_score": 0.8,
                "text_preview": "Base preview",
            }
        ],
    )

    write_jsonl(
        run_dir / "leads_with_geoadmin_locations.jsonl",
        [
            {
                "rank": 1,
                "title": "Geo lead",
                "url": "https://example.test/base",
                "source_id": "test",
                "selection_mode": "score_or_tfidf",
                "selection_score": 0.9,
                "selection_reason": "tfidf_actionable_probability >= 0.5",
                "thematic_score": 0.8,
                "tfidf_actionable_probability": 0.9,
                "text_preview": "Geo preview",
                "geoadmin_location_hint_count": 1,
                "geoadmin_top_location_name": "Bülach (ZH)",
                "geoadmin_best_location_x": 2680000.0,
                "geoadmin_best_location_y": 1260000.0,
                "geoadmin_location_hints": [
                    {
                        "name": "Bülach (ZH)",
                        "origin": "gazetteer",
                        "object_type": "municipality",
                    }
                ],
            }
        ],
    )

    report = run_review_export(run_dir=run_dir)

    review_csv = run_dir / "review" / "review_leads.csv"
    review_md = run_dir / "review" / "review_summary.md"

    assert report["records"] == 1
    assert report["records_with_geoadmin_hints"] == 1
    assert review_csv.exists()
    assert review_md.exists()

    df = pd.read_csv(review_csv)

    assert df.loc[0, "title"] == "Geo lead"
    assert df.loc[0, "selection_mode"] == "score_or_tfidf"
    assert df.loc[0, "geoadmin_top_location_name"] == "Bülach (ZH)"


def test_review_export_merges_optional_llm_explanations(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "review_test"

    write_jsonl(
        run_dir / "leads.jsonl",
        [
            {
                "rank": 1,
                "title": "Lead",
                "url": "https://example.test/lead",
                "source_id": "test",
                "thematic_score": 0.8,
                "text_preview": "Preview",
            }
        ],
    )

    write_jsonl(
        run_dir / "leads_with_llm_explanations.jsonl",
        [
            {
                "rank": 1,
                "title": "Lead",
                "url": "https://example.test/lead",
                "source_id": "test",
                "thematic_score": 0.8,
                "evidence_type": "confirmed_geometry",
                "explanation_note": "Neue Verbindung erwähnt.",
                "evidence_snippet": "neue Verbindung",
                "geometry_signal": "neue Verbindung",
                "audit_warning": "",
                "parse_success": True,
                "evidence_snippet_found_in_source": True,
                "requires_manual_check": False,
            }
        ],
    )

    report = run_review_export(run_dir=run_dir)

    df = pd.read_csv(run_dir / "review" / "review_leads.csv")

    assert report["records_with_llm_explanations"] == 1
    assert df.loc[0, "evidence_type"] == "confirmed_geometry"
    assert df.loc[0, "explanation_note"] == "Neue Verbindung erwähnt."


def test_review_export_fails_when_no_leads_exist(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "empty"

    try:
        run_review_export(run_dir=run_dir)
    except FileNotFoundError as error:
        assert "No lead output found" in str(error)
    else:
        raise AssertionError("Expected FileNotFoundError")
