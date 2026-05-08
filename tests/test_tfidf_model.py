from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from changescout.ml.tfidf_model import (
    apply_tfidf_actionable_artifact,
    train_tfidf_actionable_artifact,
)


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_train_and_apply_tfidf_artifact(tmp_path: Path):
    dataset = tmp_path / "triage_3class_dataset.csv"

    rows = [
        {
            "annotation_id": "ann_001",
            "url": "https://example.test/1",
            "source_id": "test",
            "title": "Neue Strasse Bülach",
            "text_full": "Neue Strasse und neuer Anschluss werden gebaut.",
            "triage_class": "confirmed_relevant",
            "split": "train",
        },
        {
            "annotation_id": "ann_002",
            "url": "https://example.test/2",
            "source_id": "test",
            "title": "Belag Sanierung",
            "text_full": "Der Belag wird saniert ohne Geometrieänderung.",
            "triage_class": "not_relevant",
            "split": "train",
        },
        {
            "annotation_id": "ann_003",
            "url": "https://example.test/3",
            "source_id": "test",
            "title": "Studie Ortsdurchfahrt",
            "text_full": "Plausible Umgestaltung der Ortsdurchfahrt.",
            "triage_class": "needs_review",
            "split": "train",
        },
        {
            "annotation_id": "ann_004",
            "url": "https://example.test/4",
            "source_id": "test",
            "title": "Neue Verbindung",
            "text_full": "Eine neue Verbindung und ein neuer Knoten sind vorgesehen.",
            "triage_class": "confirmed_relevant",
            "split": "test",
        },
        {
            "annotation_id": "ann_005",
            "url": "https://example.test/5",
            "source_id": "test",
            "title": "Lärmschutz",
            "text_full": "Lärmschutz und Belag ohne neue Strasse.",
            "triage_class": "not_relevant",
            "split": "test",
        },
    ]

    pd.DataFrame(rows).to_csv(dataset, index=False, encoding="utf-8")

    artifact_dir = tmp_path / "model"
    metadata = train_tfidf_actionable_artifact(
        dataset_path=dataset,
        output_dir=artifact_dir,
        model_version="test_model",
    )

    assert (artifact_dir / "model.joblib").exists()
    assert (artifact_dir / "metadata.json").exists()
    assert metadata["model_version"] == "test_model"
    assert metadata["target"] == "actionable_binary"

    scored_input = tmp_path / "run" / "scored.jsonl"
    scored_output = tmp_path / "run" / "scored_with_tfidf.jsonl"
    report_output = tmp_path / "run" / "reports" / "tfidf_inference_report.json"

    write_jsonl(
        scored_input,
        [
            {
                "title": "Neue Strasse Bülach",
                "clean_text": "Neue Strasse und neuer Anschluss werden gebaut.",
                "url": "https://example.test/run-1",
            }
        ],
    )

    report = apply_tfidf_actionable_artifact(
        input_jsonl_path=scored_input,
        output_jsonl_path=scored_output,
        report_output_path=report_output,
        artifact_dir=artifact_dir,
    )

    assert scored_output.exists()
    assert report_output.exists()
    assert report["records"] == 1
    assert report["model_version"] == "test_model"

    record = json.loads(scored_output.read_text(encoding="utf-8").splitlines()[0])
    assert "tfidf_actionable_probability" in record
    assert "tfidf_actionable_prediction" in record
    assert record["tfidf_model_version"] == "test_model"


def test_apply_tfidf_artifact_handles_empty_input(tmp_path: Path):
    dataset = tmp_path / "triage_3class_dataset.csv"

    pd.DataFrame(
        [
            {
                "annotation_id": "ann_001",
                "url": "https://example.test/1",
                "source_id": "test",
                "title": "Neue Strasse",
                "text_full": "Neue Strasse.",
                "triage_class": "confirmed_relevant",
                "split": "train",
            },
            {
                "annotation_id": "ann_002",
                "url": "https://example.test/2",
                "source_id": "test",
                "title": "Belag",
                "text_full": "Belag.",
                "triage_class": "not_relevant",
                "split": "train",
            },
            {
                "annotation_id": "ann_003",
                "url": "https://example.test/3",
                "source_id": "test",
                "title": "Neue Verbindung",
                "text_full": "Neue Verbindung.",
                "triage_class": "confirmed_relevant",
                "split": "test",
            },
            {
                "annotation_id": "ann_004",
                "url": "https://example.test/4",
                "source_id": "test",
                "title": "Lärmschutz",
                "text_full": "Lärmschutz.",
                "triage_class": "not_relevant",
                "split": "test",
            },
        ]
    ).to_csv(dataset, index=False, encoding="utf-8")

    artifact_dir = tmp_path / "model"
    train_tfidf_actionable_artifact(
        dataset_path=dataset,
        output_dir=artifact_dir,
        model_version="test_model",
    )

    empty_input = tmp_path / "empty.jsonl"
    empty_input.write_text("", encoding="utf-8")

    report = apply_tfidf_actionable_artifact(
        input_jsonl_path=empty_input,
        output_jsonl_path=tmp_path / "out.jsonl",
        report_output_path=tmp_path / "report.json",
        artifact_dir=artifact_dir,
    )

    assert report["records"] == 0
    assert report["min_probability"] is None
    assert report["max_probability"] is None
