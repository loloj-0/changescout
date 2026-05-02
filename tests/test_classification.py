from pathlib import Path
import json

import pandas as pd

from changescout.classification import (
    build_evaluable_dataset,
    compute_binary_metrics,
    create_train_test_split,
    join_annotations_with_scores,
    load_annotation_dataset,
    load_scored_pool,
    normalize_bool,
)


def test_normalize_bool_accepts_common_values():
    assert normalize_bool(True) is True
    assert normalize_bool(False) is False
    assert normalize_bool("true") is True
    assert normalize_bool("false") is False
    assert normalize_bool("1") is True
    assert normalize_bool("0") is False


def test_load_annotation_dataset_normalizes_labels(tmp_path):
    path = tmp_path / "annotations.csv"
    pd.DataFrame(
        [
            {
                "url": "https://example.test/a",
                "title": "A",
                "tlm_relevant": "true",
                "review_required": "false",
            }
        ]
    ).to_csv(path, index=False)

    result = load_annotation_dataset(path)

    assert result.loc[0, "tlm_relevant"] == True
    assert result.loc[0, "review_required"] == False


def test_load_scored_pool_requires_expected_columns(tmp_path):
    path = tmp_path / "scored.jsonl"
    record = {
        "url": "https://example.test/a",
        "document_id": "doc-a",
        "source_id": "source-a",
        "title": "A",
        "clean_text": "New road connection",
        "clean_text_length": 19,
        "thematic_score": 0.7,
    }

    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    result = load_scored_pool(path)

    assert len(result) == 1
    assert result.loc[0, "url"] == "https://example.test/a"


def test_join_annotations_with_scores_uses_url():
    annotations = pd.DataFrame(
        [
            {
                "url": "https://example.test/a",
                "title": "A",
                "tlm_relevant": True,
                "review_required": False,
            }
        ]
    )

    scored = pd.DataFrame(
        [
            {
                "url": "https://example.test/a",
                "document_id": "doc-a",
                "source_id": "source-a",
                "title": "A scored",
                "clean_text": "New road connection",
                "clean_text_length": 19,
                "thematic_score": 0.7,
                "scoring_signals": {},
            }
        ]
    )

    result = join_annotations_with_scores(annotations, scored)

    assert len(result) == 1
    assert result.loc[0, "document_id"] == "doc-a"
    assert result.loc[0, "thematic_score"] == 0.7


def test_build_evaluable_dataset_separates_review_cases():
    joined = pd.DataFrame(
        [
            {
                "url": "https://example.test/a",
                "title": "A",
                "clean_text": "New road connection",
                "tlm_relevant": True,
                "review_required": False,
            },
            {
                "url": "https://example.test/b",
                "title": "B",
                "clean_text": "Unclear bridge replacement",
                "tlm_relevant": False,
                "review_required": True,
            },
        ]
    )

    evaluable, review_set = build_evaluable_dataset(joined)

    assert len(evaluable) == 1
    assert len(review_set) == 1
    assert evaluable.loc[0, "text_input"]


def test_create_train_test_split_is_deterministic_and_stratified():
    data = pd.DataFrame(
        [
            {
                "url": f"https://example.test/true-{i}",
                "text_input": f"new road {i}",
                "tlm_relevant": True,
            }
            for i in range(10)
        ]
        + [
            {
                "url": f"https://example.test/false-{i}",
                "text_input": f"road surface {i}",
                "tlm_relevant": False,
            }
            for i in range(10)
        ]
    )

    train_1, test_1 = create_train_test_split(data, random_state=42)
    train_2, test_2 = create_train_test_split(data, random_state=42)

    assert test_1["url"].tolist() == test_2["url"].tolist()
    assert set(test_1["tlm_relevant"].unique()) == {False, True}
    assert len(train_1) + len(test_1) == len(data)


def test_compute_binary_metrics_counts_confusion_matrix():
    y_true = pd.Series([True, True, False, False])
    y_pred = pd.Series([True, False, True, False])

    metrics = compute_binary_metrics(y_true, y_pred)

    assert metrics["true_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["true_negative"] == 1