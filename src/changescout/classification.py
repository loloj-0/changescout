from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
import json

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


TEXT_COLUMNS = ["title", "clean_text"]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n"}:
        return False

    raise ValueError(f"Cannot parse boolean value: {value}")


def load_annotation_dataset(path: Path) -> pd.DataFrame:
    annotations = pd.read_csv(path)

    required_columns = {
        "url",
        "title",
        "tlm_relevant",
        "review_required",
    }

    missing_columns = required_columns - set(annotations.columns)
    if missing_columns:
        raise ValueError(f"Missing annotation columns: {sorted(missing_columns)}")

    annotations = annotations.copy()
    annotations["tlm_relevant"] = annotations["tlm_relevant"].map(normalize_bool)
    annotations["review_required"] = annotations["review_required"].map(normalize_bool)

    return annotations


def load_scored_pool(path: Path) -> pd.DataFrame:
    records = load_jsonl(path)
    scored = pd.DataFrame(records)

    required_columns = {
        "url",
        "document_id",
        "source_id",
        "title",
        "clean_text",
        "thematic_score",
    }

    missing_columns = required_columns - set(scored.columns)
    if missing_columns:
        raise ValueError(f"Missing scored columns: {sorted(missing_columns)}")

    return scored


def join_annotations_with_scores(
    annotations: pd.DataFrame,
    scored: pd.DataFrame,
) -> pd.DataFrame:
    scored_columns = [
        "url",
        "document_id",
        "source_id",
        "title",
        "clean_text",
        "clean_text_length",
        "thematic_score",
        "scoring_signals",
    ]

    available_scored_columns = [
        column for column in scored_columns if column in scored.columns
    ]

    joined = annotations.merge(
        scored[available_scored_columns],
        on="url",
        how="left",
        suffixes=("_annotation", ""),
    )

    return joined


def build_text_input(row: pd.Series) -> str:
    title = str(row.get("title", "") or "")
    clean_text = str(row.get("clean_text", "") or "")
    text_full = str(row.get("text_full", "") or "")

    body = clean_text if clean_text.strip() else text_full

    return f"{title}\n\n{body}".strip()


def build_evaluable_dataset(joined: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    review_set = joined[joined["review_required"] == True].copy()

    evaluable = joined[
        (joined["review_required"] == False)
        & joined["tlm_relevant"].notna()
    ].copy()

    evaluable["text_input"] = evaluable.apply(build_text_input, axis=1)
    evaluable = evaluable[evaluable["text_input"].str.len() > 0].copy()

    return evaluable, review_set


def create_train_test_split(
    data: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    train, test = train_test_split(
        data,
        test_size=test_size,
        random_state=random_state,
        stratify=data["tlm_relevant"],
    )

    return train.reset_index(drop=True), test.reset_index(drop=True)


def build_baseline_classifier() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.95,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train_classifier(train: pd.DataFrame) -> Pipeline:
    model = build_baseline_classifier()
    model.fit(train["text_input"], train["tlm_relevant"])

    return model


def predict_with_classifier(model: Pipeline, test: pd.DataFrame) -> pd.DataFrame:
    predictions = test.copy()
    predicted_labels = model.predict(test["text_input"])
    predicted_probabilities = model.predict_proba(test["text_input"])[:, 1]

    predictions["classifier_prediction"] = predicted_labels
    predictions["classifier_probability"] = predicted_probabilities

    return predictions


def compute_binary_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
) -> Dict[str, Any]:
    labels = [False, True]
    matrix = confusion_matrix(y_true, y_pred, labels=labels)

    tn = int(matrix[0, 0])
    fp = int(matrix[0, 1])
    fn = int(matrix[1, 0])
    tp = int(matrix[1, 1])

    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
    }


def evaluate_scoring_baseline(
    test: pd.DataFrame,
    threshold: float = 0.10,
) -> Dict[str, Any]:
    predicted = test["thematic_score"] >= threshold

    metrics = compute_binary_metrics(
        y_true=test["tlm_relevant"],
        y_pred=predicted,
    )
    metrics["threshold"] = threshold

    return metrics


def run_baseline_classification(
    annotation_path: Path,
    scored_pool_path: Path,
    test_size: float = 0.2,
    random_state: int = 42,
    scoring_threshold: float = 0.10,
) -> Dict[str, Any]:
    annotations = load_annotation_dataset(annotation_path)
    scored = load_scored_pool(scored_pool_path)
    joined = join_annotations_with_scores(annotations, scored)

    missing_scores = int(joined["thematic_score"].isna().sum())
    if missing_scores:
        raise ValueError(f"{missing_scores} annotated records have no matching score")

    evaluable, review_set = build_evaluable_dataset(joined)
    train, test = create_train_test_split(
        evaluable,
        test_size=test_size,
        random_state=random_state,
    )

    model = train_classifier(train)
    predictions = predict_with_classifier(model, test)

    classifier_metrics = compute_binary_metrics(
        y_true=predictions["tlm_relevant"],
        y_pred=predictions["classifier_prediction"],
    )

    scoring_metrics = evaluate_scoring_baseline(
        test=predictions,
        threshold=scoring_threshold,
    )

    return {
        "joined": joined,
        "evaluable": evaluable,
        "review_set": review_set,
        "train": train,
        "test": test,
        "predictions": predictions,
        "model": model,
        "metrics": {
            "dataset": {
                "total_annotations": int(len(annotations)),
                "evaluable_records": int(len(evaluable)),
                "review_records": int(len(review_set)),
                "train_records": int(len(train)),
                "test_records": int(len(test)),
                "random_state": random_state,
                "test_size": test_size,
            },
            "classifier": classifier_metrics,
            "scoring_baseline": scoring_metrics,
        },
    }