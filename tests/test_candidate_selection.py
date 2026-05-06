from __future__ import annotations

import json
from pathlib import Path

import pytest

from changescout.candidate_selection import run_candidate_selection


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_score_or_tfidf_selects_by_score_or_tfidf_probability(tmp_path: Path):
    input_path = tmp_path / "scored_with_tfidf.jsonl"
    output_jsonl = tmp_path / "leads.jsonl"
    output_csv = tmp_path / "leads.csv"
    report_path = tmp_path / "reports" / "lead_generation_report.json"

    write_jsonl(
        input_path,
        [
            {
                "title": "A high score",
                "url": "https://example.test/a",
                "clean_text": "A",
                "thematic_score": 0.8,
                "tfidf_actionable_probability": 0.2,
            },
            {
                "title": "B high tfidf",
                "url": "https://example.test/b",
                "clean_text": "B",
                "thematic_score": 0.1,
                "tfidf_actionable_probability": 0.9,
            },
            {
                "title": "C below both",
                "url": "https://example.test/c",
                "clean_text": "C",
                "thematic_score": 0.1,
                "tfidf_actionable_probability": 0.2,
            },
        ],
    )

    report = run_candidate_selection(
        input_jsonl_path=input_path,
        output_jsonl_path=output_jsonl,
        output_csv_path=output_csv,
        report_output_path=report_path,
        mode="score_or_tfidf",
        score_threshold=0.5,
        tfidf_threshold=0.5,
        preview_length=20,
    )

    leads = read_jsonl(output_jsonl)

    assert report["lead_count"] == 2
    assert output_csv.exists()
    assert report_path.exists()

    assert [lead["title"] for lead in leads] == ["B high tfidf", "A high score"]
    assert leads[0]["selection_mode"] == "score_or_tfidf"
    assert leads[0]["selection_score"] == 0.9
    assert leads[0]["rank"] == 1
    assert leads[1]["rank"] == 2
    assert "tfidf_actionable_probability" in leads[0]
    assert "selection_reason" in leads[0]


def test_score_only_is_deterministic(tmp_path: Path):
    input_path = tmp_path / "scored.jsonl"
    output_jsonl = tmp_path / "leads.jsonl"

    write_jsonl(
        input_path,
        [
            {
                "title": "B title",
                "url": "https://example.test/b",
                "clean_text": "B",
                "thematic_score": 0.7,
            },
            {
                "title": "A title",
                "url": "https://example.test/a",
                "clean_text": "A",
                "thematic_score": 0.7,
            },
        ],
    )

    run_candidate_selection(
        input_jsonl_path=input_path,
        output_jsonl_path=output_jsonl,
        output_csv_path=tmp_path / "leads.csv",
        report_output_path=tmp_path / "report.json",
        mode="score_only",
        score_threshold=0.1,
    )

    leads = read_jsonl(output_jsonl)

    assert [lead["title"] for lead in leads] == ["A title", "B title"]


def test_score_or_tfidf_requires_tfidf_probability(tmp_path: Path):
    input_path = tmp_path / "scored.jsonl"

    write_jsonl(
        input_path,
        [
            {
                "title": "Missing tfidf",
                "url": "https://example.test/missing",
                "clean_text": "Missing",
                "thematic_score": 0.9,
            }
        ],
    )

    report = run_candidate_selection(
        input_jsonl_path=input_path,
        output_jsonl_path=tmp_path / "leads.jsonl",
        output_csv_path=tmp_path / "leads.csv",
        report_output_path=tmp_path / "report.json",
        mode="score_or_tfidf",
        score_threshold=0.1,
        tfidf_threshold=0.5,
    )

    assert report["lead_count"] == 0
    assert report["missing_tfidf_probability_count"] == 1


def test_unsupported_mode_fails(tmp_path: Path):
    input_path = tmp_path / "scored.jsonl"
    input_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        run_candidate_selection(
            input_jsonl_path=input_path,
            output_jsonl_path=tmp_path / "leads.jsonl",
            output_csv_path=tmp_path / "leads.csv",
            report_output_path=tmp_path / "report.json",
            mode="bad_mode",
            score_threshold=0.1,
        )
