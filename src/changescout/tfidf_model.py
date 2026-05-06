from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import json

from joblib import dump, load
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline


ACTIONABLE_CLASSES = {"confirmed_relevant", "needs_review"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    return str(value).strip()


def build_model_text_from_values(title: Any, text: Any) -> str:
    return normalize_text(title) + "\n\n" + normalize_text(text)


def build_model_text_for_record(record: Dict[str, Any]) -> str:
    title = record.get("title", "")

    text = (
        record.get("clean_text")
        or record.get("text_full")
        or record.get("text_preview")
        or record.get("preview")
        or ""
    )

    return build_model_text_from_values(title, text)


def build_tfidf_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents=None,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.95,
                    sublinear_tf=True,
                    max_features=20000,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                    solver="liblinear",
                ),
            ),
        ]
    )


def metric_dict(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    return {
        "records": int(len(y_true)),
        "positive_count": int((y_true == 1).sum()),
        "negative_count": int((y_true == 0).sum()),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def prepare_training_dataframe(dataset_path: Path) -> pd.DataFrame:
    df = pd.read_csv(dataset_path)

    required_columns = [
        "annotation_id",
        "title",
        "text_full",
        "triage_class",
        "split",
    ]

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {dataset_path}: {missing}")

    result = df.copy()
    result["model_text"] = [
        build_model_text_from_values(title, text)
        for title, text in zip(result["title"], result["text_full"])
    ]
    result["target_actionable"] = result["triage_class"].isin(ACTIONABLE_CLASSES).astype(int)

    return result


def train_tfidf_actionable_artifact(
    dataset_path: Path,
    output_dir: Path,
    model_version: str,
    train_split: str = "train",
    test_split: str = "test",
) -> Dict[str, Any]:
    df = prepare_training_dataframe(dataset_path)

    train_df = df[df["split"] == train_split].copy()
    test_df = df[df["split"] == test_split].copy()

    if train_df.empty:
        raise ValueError(f"No records for train split: {train_split}")

    if test_df.empty:
        raise ValueError(f"No records for test split: {test_split}")

    model = build_tfidf_pipeline()
    model.fit(train_df["model_text"], train_df["target_actionable"].astype(int))

    prediction = model.predict(test_df["model_text"])
    probability = model.predict_proba(test_df["model_text"])[:, 1]

    metrics = metric_dict(
        y_true=test_df["target_actionable"].astype(int),
        y_pred=pd.Series(prediction, index=test_df.index),
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "model.joblib"
    metadata_path = output_dir / "metadata.json"

    dump(model, model_path)

    metadata = {
        "model_version": model_version,
        "model_type": "tfidf_logistic_regression",
        "target": "actionable_binary",
        "positive_classes": sorted(ACTIONABLE_CLASSES),
        "created_at": utc_now_iso(),
        "training_dataset_path": str(dataset_path),
        "training_dataset_sha256": sha256_file(dataset_path),
        "train_split": train_split,
        "test_split": test_split,
        "train_records": int(len(train_df)),
        "test_records": int(len(test_df)),
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "threshold": 0.5,
        "metrics": metrics,
        "tfidf": {
            "ngram_range": [1, 2],
            "min_df": 1,
            "max_df": 0.95,
            "sublinear_tf": True,
            "max_features": 20000,
        },
        "classifier": {
            "type": "LogisticRegression",
            "class_weight": "balanced",
            "solver": "liblinear",
            "max_iter": 2000,
            "random_state": 42,
        },
    }

    write_json(metadata_path, metadata)

    predictions = test_df[
        [
            "annotation_id",
            "split",
            "url",
            "source_id",
            "title",
            "triage_class",
            "target_actionable",
        ]
    ].copy()

    predictions["tfidf_actionable_prediction"] = prediction
    predictions["tfidf_actionable_probability"] = probability
    predictions.to_csv(
        output_dir / "test_predictions.csv",
        index=False,
        encoding="utf-8",
    )

    return metadata


def load_tfidf_artifact(artifact_dir: Path) -> tuple[Pipeline, Dict[str, Any]]:
    metadata_path = artifact_dir / "metadata.json"
    metadata = load_json(metadata_path)

    model_path = artifact_dir / "model.joblib"
    if not model_path.exists():
        model_path = Path(str(metadata.get("model_path", "")))

    if not model_path.exists():
        raise FileNotFoundError(model_path)

    model = load(model_path)

    return model, metadata


def apply_tfidf_actionable_artifact(
    input_jsonl_path: Path,
    output_jsonl_path: Path,
    report_output_path: Path,
    artifact_dir: Path,
    threshold: Optional[float] = None,
) -> Dict[str, Any]:
    model, metadata = load_tfidf_artifact(artifact_dir)

    records = read_jsonl(input_jsonl_path)
    model_texts = [build_model_text_for_record(record) for record in records]
    empty_model_text_count = sum(1 for text in model_texts if not text.strip())

    if records:
        probabilities = list(model.predict_proba(model_texts)[:, 1])
    else:
        probabilities = []

    used_threshold = float(
        threshold if threshold is not None else metadata.get("threshold", 0.5)
    )

    output_records: List[Dict[str, Any]] = []

    for record, probability in zip(records, probabilities):
        probability_value = float(probability)

        enriched = dict(record)
        enriched["tfidf_model_version"] = metadata.get("model_version", "")
        enriched["tfidf_actionable_probability"] = probability_value
        enriched["tfidf_actionable_prediction"] = probability_value >= used_threshold
        enriched["tfidf_actionable_threshold"] = used_threshold

        output_records.append(enriched)

    write_jsonl(output_jsonl_path, output_records)

    report = {
        "input_path": str(input_jsonl_path),
        "output_path": str(output_jsonl_path),
        "artifact_dir": str(artifact_dir),
        "model_version": metadata.get("model_version", ""),
        "target": metadata.get("target", ""),
        "records": int(len(records)),
        "empty_model_text_count": int(empty_model_text_count),
        "threshold": used_threshold,
        "predicted_actionable_count": int(
            sum(1 for record in output_records if record.get("tfidf_actionable_prediction") is True)
        ),
        "min_probability": float(min(probabilities)) if probabilities else None,
        "max_probability": float(max(probabilities)) if probabilities else None,
        "mean_probability": float(sum(probabilities) / len(probabilities)) if probabilities else None,
    }

    write_json(report_output_path, report)

    return report
