import json
from pathlib import Path

import pandas as pd

from changescout.leads import (
    build_lead_generation_report,
    enrich_with_classifier_predictions,
    generate_leads,
    load_scored_documents,
    make_text_preview,
)


def test_load_scored_documents_requires_expected_columns(tmp_path):
    path = tmp_path / "scored.jsonl"
    record = {
        "document_id": "doc-a",
        "source_id": "source-a",
        "url": "https://example.test/a",
        "title": "A",
        "clean_text": "New road connection",
        "thematic_score": 0.42,
    }

    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    result = load_scored_documents(path)

    assert len(result) == 1
    assert result.loc[0, "thematic_score"] == 0.42


def test_make_text_preview_normalizes_whitespace_and_truncates():
    text = "This   is\n\n a   long text with   spacing."

    result = make_text_preview(text, max_length=12)

    assert result == "This is a lo"


def test_enrich_with_classifier_predictions_joins_on_url():
    scored = pd.DataFrame(
        [
            {
                "url": "https://example.test/a",
                "thematic_score": 0.3,
            }
        ]
    )

    predictions = pd.DataFrame(
        [
            {
                "url": "https://example.test/a",
                "classifier_prediction": True,
                "classifier_probability": 0.8,
            }
        ]
    )

    result = enrich_with_classifier_predictions(scored, predictions)

    assert result.loc[0, "classifier_prediction"] == True
    assert result.loc[0, "classifier_probability"] == 0.8


def test_generate_leads_filters_and_sorts_deterministically():
    documents = pd.DataFrame(
        [
            {
                "document_id": "doc-low",
                "source_id": "source",
                "url": "https://example.test/low",
                "title": "Low",
                "clean_text": "Low score",
                "thematic_score": 0.05,
            },
            {
                "document_id": "doc-b",
                "source_id": "source",
                "url": "https://example.test/b",
                "title": "B title",
                "clean_text": "High score B",
                "thematic_score": 0.8,
            },
            {
                "document_id": "doc-a",
                "source_id": "source",
                "url": "https://example.test/a",
                "title": "A title",
                "clean_text": "High score A",
                "thematic_score": 0.8,
            },
        ]
    )

    result = generate_leads(documents, threshold=0.1)

    assert result["document_id"].tolist() == ["doc-a", "doc-b"]
    assert result["lead_reason"].tolist() == [
        "thematic_score >= 0.10",
        "thematic_score >= 0.10",
    ]


def test_build_lead_generation_report_counts_inputs_and_leads():
    documents = pd.DataFrame(
        [
            {"thematic_score": 0.1},
            {"thematic_score": 0.5},
            {"thematic_score": 0.0},
        ]
    )
    leads = pd.DataFrame(
        [
            {"thematic_score": 0.1},
            {"thematic_score": 0.5},
        ]
    )

    result = build_lead_generation_report(
        documents=documents,
        leads=leads,
        threshold=0.1,
    )

    assert result["input_documents"] == 3
    assert result["lead_count"] == 2
    assert result["threshold"] == 0.1
    assert result["max_score"] == 0.5