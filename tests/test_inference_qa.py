from __future__ import annotations

import json
from pathlib import Path

from changescout.review.inference_qa import build_inference_qa_report, run_inference_qa


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_inference_qa_passes_for_valid_hybrid_run(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "qa_valid"

    write_json(
        run_dir / "metadata" / "run_metadata.json",
        {
            "paths": {
                "scored_with_tfidf": str(run_dir / "scored_with_tfidf.jsonl")
            },
            "report_paths": {
                "tfidf_inference": str(run_dir / "reports" / "tfidf_inference_report.json")
            },
        },
    )

    write_jsonl(
        run_dir / "scored.jsonl",
        [
            {
                "url": "https://example.test/project",
                "title": "Project",
                "clean_text": "Long enough text",
            }
        ],
    )

    write_jsonl(
        run_dir / "scored_with_tfidf.jsonl",
        [
            {
                "url": "https://example.test/project",
                "title": "Project",
                "tfidf_actionable_probability": 0.8,
            }
        ],
    )

    write_jsonl(
        run_dir / "leads.jsonl",
        [
            {
                "rank": 1,
                "url": "https://example.test/project",
                "title": "Project",
                "text_preview": "Preview",
                "selection_reason": "tfidf_actionable_probability >= 0.5",
                "tfidf_actionable_probability": 0.8,
            }
        ],
    )

    report = build_inference_qa_report(run_dir)

    assert report["status"] == "pass"
    assert report["counts"]["lead_records"] == 1
    assert report["counts"]["missing_tfidf_probability_count"] == 0
    assert report["error_count"] == 0


def test_inference_qa_fails_when_hybrid_lead_has_missing_tfidf(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "qa_missing_tfidf"

    write_json(
        run_dir / "metadata" / "run_metadata.json",
        {
            "paths": {
                "scored_with_tfidf": str(run_dir / "scored_with_tfidf.jsonl")
            }
        },
    )

    write_jsonl(run_dir / "scored_with_tfidf.jsonl", [{"url": "https://example.test/a"}])

    write_jsonl(
        run_dir / "leads.jsonl",
        [
            {
                "rank": 1,
                "url": "https://example.test/a",
                "title": "A",
                "text_preview": "Preview",
                "selection_reason": "thematic_score >= 0.1",
            }
        ],
    )

    report = build_inference_qa_report(run_dir)

    assert report["status"] == "fail"
    assert report["counts"]["missing_tfidf_probability_count"] == 1
    assert any(
        warning["code"] == "missing_tfidf_probability"
        for warning in report["warnings"]
    )


def test_inference_qa_detects_duplicate_urls(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "qa_duplicates"

    write_jsonl(
        run_dir / "leads.jsonl",
        [
            {
                "rank": 1,
                "url": "https://example.test/project/",
                "title": "A",
                "text_preview": "Preview",
                "selection_reason": "thematic_score >= 0.1",
            },
            {
                "rank": 2,
                "url": "https://example.test/project",
                "title": "A duplicate",
                "text_preview": "Preview",
                "selection_reason": "thematic_score >= 0.1",
            },
        ],
    )

    report = build_inference_qa_report(run_dir)

    assert report["status"] == "pass"
    assert report["counts"]["duplicate_url_group_count"] == 1
    assert any(warning["code"] == "duplicate_urls" for warning in report["warnings"])


def test_run_inference_qa_writes_json_and_markdown(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "qa_write"

    write_jsonl(
        run_dir / "leads.jsonl",
        [
            {
                "rank": 1,
                "url": "https://example.test/project",
                "title": "Project",
                "text_preview": "Preview",
                "selection_reason": "thematic_score >= 0.1",
            }
        ],
    )

    report = run_inference_qa(run_dir)

    assert report["status"] == "pass"
    assert (run_dir / "reports" / "inference_qa_report.json").exists()
    assert (run_dir / "reports" / "inference_qa_report.md").exists()
