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


THRESHOLDS = [
    0.0,
    0.02,
    0.05,
    0.1,
    0.15,
    0.2,
    0.25,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
]


LLM_PREDICTION_PATHS = {
    "Qwen2.5 7B hierarchical": "data/annotation/evaluation/local_llm/Qwen__Qwen2.5-7B-Instruct/hierarchical/llm_triage_predictions.jsonl",
    "Qwen2.5 7B direct": "data/annotation/evaluation/local_llm/Qwen__Qwen2.5-7B-Instruct/direct/llm_triage_predictions.jsonl",
    "Llama 3.1 8B hierarchical": "data/annotation/evaluation/local_llm/meta-llama__Llama-3.1-8B-Instruct/hierarchical/llm_triage_predictions.jsonl",
    "Qwen2.5 14B hierarchical": "data/annotation/evaluation/local_llm/Qwen__Qwen2.5-14B-Instruct/hierarchical/llm_triage_predictions.jsonl",
    "Qwen2.5 14B direct": "data/annotation/evaluation/local_llm/Qwen__Qwen2.5-14B-Instruct/direct/llm_triage_predictions.jsonl",
}


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
    result["model_text"] = (
        result["title"].fillna("").astype(str)
        + "\n\n"
        + result["text_full"].fillna("").astype(str)
    )
    return result


def get_score_column(df: pd.DataFrame) -> str:
    if "score" in df.columns:
        return "score"
    if "thematic_score" in df.columns:
        return "thematic_score"
    raise ValueError("Expected either 'score' or 'thematic_score' column")


def metric_dict(y_true: pd.Series, y_pred: pd.Series) -> dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    return {
        "records": int(len(y_true)),
        "positives": int((y_true == 1).sum()),
        "negatives": int((y_true == 0).sum()),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def prepare_task_dataset(df: pd.DataFrame, task: str) -> pd.DataFrame:
    result = df.copy()

    if task == "strict_binary":
        result = result[result["triage_class"].isin(["confirmed_relevant", "not_relevant"])].copy()
        result["target"] = (result["triage_class"] == "confirmed_relevant").astype(int)
        return result

    if task == "actionable_binary":
        result["target"] = result["triage_class"].isin(["confirmed_relevant", "needs_review"]).astype(int)
        return result

    raise ValueError(f"Unknown task: {task}")


def select_score_threshold(train_df: pd.DataFrame, score_column: str) -> tuple[float, dict[str, Any]]:
    best_threshold = None
    best_metrics = None

    for threshold in THRESHOLDS:
        y_true = train_df["target"].astype(int)
        y_pred = (train_df[score_column].astype(float) >= threshold).astype(int)
        metrics = metric_dict(y_true, y_pred)
        metrics["threshold"] = threshold

        if best_metrics is None:
            best_threshold = threshold
            best_metrics = metrics
            continue

        current_key = (
            metrics["f1"],
            metrics["recall"],
            metrics["precision"],
            -threshold,
        )
        best_key = (
            best_metrics["f1"],
            best_metrics["recall"],
            best_metrics["precision"],
            -float(best_metrics["threshold"]),
        )

        if current_key > best_key:
            best_threshold = threshold
            best_metrics = metrics

    if best_threshold is None or best_metrics is None:
        raise ValueError("No threshold selected")

    return best_threshold, best_metrics


def evaluate_score(df: pd.DataFrame, task: str) -> dict[str, Any]:
    task_df = prepare_task_dataset(df, task)
    score_column = get_score_column(task_df)

    train_df = task_df[task_df["split"] == "train"].copy()
    test_df = task_df[task_df["split"] == "test"].copy()

    threshold, train_metrics = select_score_threshold(train_df, score_column)

    y_true = test_df["target"].astype(int)
    y_pred = (test_df[score_column].astype(float) >= threshold).astype(int)

    metrics = metric_dict(y_true, y_pred)
    metrics["selected_threshold"] = threshold
    metrics["train_selection_metrics"] = train_metrics

    return metrics


def evaluate_tfidf(df: pd.DataFrame, task: str) -> tuple[dict[str, Any], pd.DataFrame]:
    task_df = prepare_task_dataset(df, task)
    task_df = add_model_text(task_df)

    train_df = task_df[task_df["split"] == "train"].copy()
    test_df = task_df[task_df["split"] == "test"].copy()

    model = build_model()
    model.fit(train_df["model_text"], train_df["target"].astype(int))

    prediction = model.predict(test_df["model_text"])
    probability = model.predict_proba(test_df["model_text"])[:, 1]

    metrics = metric_dict(test_df["target"].astype(int), pd.Series(prediction))

    predictions = test_df[
        [
            "annotation_id",
            "split",
            "url",
            "source_id",
            "title",
            "triage_class",
            "target",
        ]
    ].copy()

    predictions["method"] = "TF IDF Logistic Regression"
    predictions["task"] = task
    predictions["prediction"] = prediction
    predictions["probability"] = probability

    return metrics, predictions


def load_llm_predictions(path: Path) -> pd.DataFrame:
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return pd.DataFrame(records)


def llm_prediction_to_target(predicted_class: str, task: str) -> int:
    if task == "strict_binary":
        return 1 if predicted_class == "confirmed_relevant" else 0

    if task == "actionable_binary":
        return 1 if predicted_class in ["confirmed_relevant", "needs_review"] else 0

    raise ValueError(f"Unknown task: {task}")


def evaluate_llm(df: pd.DataFrame, task: str, method_name: str, prediction_path: Path) -> dict[str, Any]:
    task_df = prepare_task_dataset(df, task)
    test_df = task_df[task_df["split"] == "test"].copy()

    llm_df = load_llm_predictions(prediction_path)

    merged = test_df.merge(
        llm_df[["annotation_id", "triage_class"]].rename(columns={"triage_class": "llm_triage_class"}),
        on="annotation_id",
        how="left",
    )

    missing = merged["llm_triage_class"].isna().sum()
    if missing:
        raise ValueError(f"{method_name} is missing {missing} predictions for {task}")

    y_true = merged["target"].astype(int)
    y_pred = merged["llm_triage_class"].map(lambda value: llm_prediction_to_target(str(value), task)).astype(int)

    metrics = metric_dict(y_true, y_pred)
    metrics["missing_predictions"] = int(missing)

    return metrics


def build_markdown(rows: list[dict[str, Any]]) -> str:
    df = pd.DataFrame(rows)

    lines = [
        "# Aligned Method Comparison",
        "",
        "All methods are evaluated on the same frozen triage test split.",
        "",
        "Strict binary excludes needs_review cases.",
        "",
        "Actionable binary maps confirmed_relevant and needs_review to positive.",
        "",
        "| Task | Method | Type | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    ordered = df.sort_values(["task", "f1", "recall"], ascending=[True, False, False])

    for _, row in ordered.iterrows():
        lines.append(
            "| "
            f"{row['task']} | "
            f"{row['method']} | "
            f"{row['method_type']} | "
            f"{row['precision']:.3f} | "
            f"{row['recall']:.3f} | "
            f"{row['f1']:.3f} | "
            f"{row['accuracy']:.3f} | "
            f"{int(row['tp'])} | "
            f"{int(row['fp'])} | "
            f"{int(row['tn'])} | "
            f"{int(row['fn'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This report removes the split alignment issue by evaluating all methods on the same triage test records.",
            "",
            "The TF IDF classifier is trained on the corresponding triage train split for each binary target.",
            "",
            "The score baseline threshold is selected on the corresponding triage train split.",
            "",
            "Local LLM predictions are evaluated on the same triage test split without additional inference.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate all methods on aligned triage test records.")
    parser.add_argument(
        "--input",
        default="data/annotation/evaluation/triage_3class_dataset.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="data/annotation/evaluation/aligned_method_comparison",
    )

    args = parser.parse_args()

    df = pd.read_csv(args.input)

    rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []

    for task in ["strict_binary", "actionable_binary"]:
        score_metrics = evaluate_score(df, task)
        rows.append(
            {
                "task": task,
                "method": "thematic_score",
                "method_type": "deterministic_score",
                **score_metrics,
            }
        )

        tfidf_metrics, tfidf_predictions = evaluate_tfidf(df, task)
        rows.append(
            {
                "task": task,
                "method": "TF IDF Logistic Regression",
                "method_type": "classical_ml",
                **tfidf_metrics,
            }
        )
        prediction_frames.append(tfidf_predictions)

        for method_name, prediction_path in LLM_PREDICTION_PATHS.items():
            path = Path(prediction_path)
            if not path.exists():
                continue

            llm_metrics = evaluate_llm(df, task, method_name, path)
            rows.append(
                {
                    "task": task,
                    "method": method_name,
                    "method_type": "local_llm",
                    **llm_metrics,
                }
            )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_json = output_dir / "aligned_method_comparison.json"
    output_csv = output_dir / "aligned_method_comparison.csv"
    output_md = output_dir / "aligned_method_comparison.md"
    output_predictions = output_dir / "aligned_tfidf_predictions.csv"

    output_json.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    pd.DataFrame(rows).to_csv(output_csv, index=False, encoding="utf-8")
    output_md.write_text(build_markdown(rows), encoding="utf-8")

    if prediction_frames:
        pd.concat(prediction_frames, ignore_index=True).to_csv(
            output_predictions,
            index=False,
            encoding="utf-8",
        )

    print(f"Wrote {output_json}")
    print(f"Wrote {output_csv}")
    print(f"Wrote {output_md}")
    print(f"Wrote {output_predictions}")
    print()
    print(pd.DataFrame(rows).sort_values(["task", "f1", "recall"], ascending=[True, False, False]).to_string(index=False))


if __name__ == "__main__":
    main()
