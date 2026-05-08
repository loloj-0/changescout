from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline


DATASETS = {
    "strict_binary": {
        "path": Path("data/annotation/evaluation/strict_binary_dataset.csv"),
        "target_column": "target_strict_relevant",
    },
    "actionable_binary": {
        "path": Path("data/annotation/evaluation/actionable_binary_dataset.csv"),
        "target_column": "target_actionable",
    },
}


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_model() -> Pipeline:
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


def add_model_text(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    title = result["title"].fillna("").astype(str)
    text = result["text_full"].fillna("").astype(str)

    result["model_text"] = title + "\n\n" + text

    return result


def metric_dict(y_true: pd.Series, y_pred: pd.Series) -> dict[str, Any]:
    labels = [0, 1]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=labels).ravel()

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


def load_score_baseline_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    result = {}

    for row in data.get("selected_threshold_test_metrics", []):
        dataset = row.get("dataset")
        if dataset:
            result[dataset] = row

    return result


def evaluate_dataset(
    dataset_name: str,
    path: Path,
    target_column: str,
) -> tuple[dict[str, Any], pd.DataFrame]:
    df = pd.read_csv(path)
    df = add_model_text(df)

    required_columns = [
        "annotation_id",
        "url",
        "source_id",
        "title",
        "text_full",
        "split",
        "triage_class",
        target_column,
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in {path}: {missing_columns}")

    train = df[df["split"] == "train"].copy()
    test = df[df["split"] == "test"].copy()

    if train.empty or test.empty:
        raise ValueError(f"Dataset {dataset_name} must contain train and test records")

    model = build_model()

    x_train = train["model_text"]
    y_train = train[target_column].astype(int)

    x_test = test["model_text"]
    y_test = test[target_column].astype(int)

    model.fit(x_train, y_train)

    prediction = model.predict(x_test)
    probability = model.predict_proba(x_test)[:, 1]

    metrics = metric_dict(y_test, pd.Series(prediction, index=test.index))

    predictions = test.copy()
    predictions["classifier_prediction"] = prediction
    predictions["classifier_probability"] = probability
    predictions["target_column"] = target_column
    predictions["dataset"] = dataset_name

    keep_columns = [
        "dataset",
        "annotation_id",
        "split",
        "url",
        "source_id",
        "title",
        "triage_class",
        target_column,
        "classifier_prediction",
        "classifier_probability",
        "score",
        "change_type",
        "notes",
    ]

    keep_columns = [column for column in keep_columns if column in predictions.columns]

    return metrics, predictions[keep_columns]


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Classical Text Classifier Evaluation",
        "",
        "## Method",
        "",
        "This evaluation uses a TF IDF plus Logistic Regression classifier.",
        "The frozen train and test splits from Issue 15 are used.",
        "The model is evaluated on the same strict binary and actionable binary datasets as the score baseline.",
        "",
        "## Test metrics",
        "",
    ]

    for dataset_name, metrics in report["classifier_metrics"].items():
        lines.extend(
            [
                f"### {dataset_name}",
                "",
                f"* Records: `{metrics['records']}`",
                f"* Positives: `{metrics['positive_count']}`",
                f"* Negatives: `{metrics['negative_count']}`",
                f"* TP: `{metrics['tp']}`",
                f"* FP: `{metrics['fp']}`",
                f"* TN: `{metrics['tn']}`",
                f"* FN: `{metrics['fn']}`",
                f"* Precision: `{metrics['precision']:.3f}`",
                f"* Recall: `{metrics['recall']:.3f}`",
                f"* F1: `{metrics['f1']:.3f}`",
                f"* Accuracy: `{metrics['accuracy']:.3f}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Comparison with score baseline",
            "",
        ]
    )

    for dataset_name, comparison in report["comparison_with_score_baseline"].items():
        lines.extend(
            [
                f"### {dataset_name}",
                "",
                f"* Classifier F1: `{comparison['classifier_f1']:.3f}`",
                f"* Score baseline F1: `{comparison['score_f1']:.3f}`",
                f"* Classifier recall: `{comparison['classifier_recall']:.3f}`",
                f"* Score baseline recall: `{comparison['score_recall']:.3f}`",
                f"* Classifier precision: `{comparison['classifier_precision']:.3f}`",
                f"* Score baseline precision: `{comparison['score_precision']:.3f}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation",
            "",
            "This classifier is a learned non LLM baseline.",
            "It tests whether a simple supervised text model improves over deterministic score based prioritization.",
            "For the ChangeScout workflow, recall and lead usefulness are more important than accuracy alone.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate TF IDF Logistic Regression baseline on frozen evaluation datasets."
    )
    parser.add_argument(
        "--output-dir",
        default="data/annotation/evaluation/classical_text_classifier",
    )
    parser.add_argument(
        "--score-baseline-report",
        default="data/annotation/evaluation/score_baseline/score_baseline_report.json",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    score_baseline = load_score_baseline_metrics(Path(args.score_baseline_report))

    classifier_metrics: dict[str, Any] = {}
    prediction_frames = []

    for dataset_name, config in DATASETS.items():
        metrics, predictions = evaluate_dataset(
            dataset_name=dataset_name,
            path=config["path"],
            target_column=config["target_column"],
        )

        classifier_metrics[dataset_name] = metrics
        prediction_frames.append(predictions)

    predictions_df = pd.concat(prediction_frames, ignore_index=True)

    comparison = {}

    for dataset_name, metrics in classifier_metrics.items():
        score_metrics = score_baseline.get(dataset_name, {})

        if score_metrics:
            comparison[dataset_name] = {
                "classifier_precision": metrics["precision"],
                "classifier_recall": metrics["recall"],
                "classifier_f1": metrics["f1"],
                "classifier_accuracy": metrics["accuracy"],
                "score_precision": float(score_metrics.get("precision", 0.0)),
                "score_recall": float(score_metrics.get("recall", 0.0)),
                "score_f1": float(score_metrics.get("f1", 0.0)),
                "score_accuracy": float(score_metrics.get("accuracy", 0.0)),
            }

    metrics_path = output_dir / "classical_text_classifier_metrics.json"
    predictions_path = output_dir / "classical_text_classifier_predictions.csv"
    report_md_path = output_dir / "classical_text_classifier_report.md"

    report = {
        "method": {
            "model": "TF IDF plus Logistic Regression",
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
        },
        "datasets": {
            name: {
                "path": str(config["path"]),
                "target_column": config["target_column"],
            }
            for name, config in DATASETS.items()
        },
        "classifier_metrics": classifier_metrics,
        "comparison_with_score_baseline": comparison,
        "outputs": {
            "metrics": str(metrics_path),
            "predictions": str(predictions_path),
            "report_md": str(report_md_path),
        },
    }

    write_json(metrics_path, report)
    predictions_df.to_csv(predictions_path, index=False, encoding="utf-8")
    report_md_path.write_text(build_markdown_report(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
