from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


THRESHOLDS = [
    0.00,
    0.02,
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.40,
    0.50,
    0.60,
    0.70,
    0.80,
    0.90,
]

AT_N_VALUES = [10, 20, 50, 100]


def get_score_column(df: pd.DataFrame) -> str:
    if "thematic_score" in df.columns:
        return "thematic_score"

    if "score" in df.columns:
        return "score"

    raise ValueError("Dataset must contain either thematic_score or score")


def confusion_counts(y_true: pd.Series, y_pred: pd.Series) -> dict[str, int]:
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def metrics_from_counts(counts: dict[str, int]) -> dict[str, float | int]:
    tp = counts["tp"]
    fp = counts["fp"]
    tn = counts["tn"]
    fn = counts["fn"]

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    accuracy = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) else 0.0

    return {
        **counts,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def evaluate_thresholds(
    df: pd.DataFrame,
    dataset_name: str,
    split_name: str,
    target_column: str,
    score_column: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    subset = df[df["split"] == split_name].copy()

    if subset.empty:
        raise ValueError(f"No records for split {split_name} in {dataset_name}")

    y_true = subset[target_column].astype(int)

    for threshold in THRESHOLDS:
        y_pred = (subset[score_column] >= threshold).astype(int)
        counts = confusion_counts(y_true, y_pred)
        metrics = metrics_from_counts(counts)

        rows.append(
            {
                "dataset": dataset_name,
                "split": split_name,
                "threshold": threshold,
                "records": int(len(subset)),
                "positives": int(y_true.sum()),
                "negatives": int((y_true == 0).sum()),
                **metrics,
            }
        )

    return rows


def select_best_threshold(threshold_rows: list[dict[str, Any]], dataset_name: str) -> float:
    candidates = [
        row
        for row in threshold_rows
        if row["dataset"] == dataset_name and row["split"] == "train"
    ]

    if not candidates:
        raise ValueError(f"No train threshold rows found for {dataset_name}")

    best = sorted(
        candidates,
        key=lambda row: (
            row["f1"],
            row["recall"],
            row["precision"],
            -row["threshold"],
        ),
        reverse=True,
    )[0]

    return float(best["threshold"])


def evaluate_at_n(
    df: pd.DataFrame,
    dataset_name: str,
    split_name: str,
    target_column: str,
    score_column: str,
) -> list[dict[str, Any]]:
    subset = df[df["split"] == split_name].copy()

    if subset.empty:
        raise ValueError(f"No records for split {split_name} in {dataset_name}")

    subset = subset.sort_values(score_column, ascending=False).reset_index(drop=True)
    total_positives = int(subset[target_column].astype(int).sum())

    rows: list[dict[str, Any]] = []

    for n in AT_N_VALUES:
        effective_n = min(n, len(subset))
        top_n = subset.head(effective_n)
        true_positives_at_n = int(top_n[target_column].astype(int).sum())

        precision_at_n = true_positives_at_n / effective_n if effective_n else 0.0
        recall_at_n = (
            true_positives_at_n / total_positives
            if total_positives
            else 0.0
        )

        rows.append(
            {
                "dataset": dataset_name,
                "split": split_name,
                "n": n,
                "effective_n": effective_n,
                "records": int(len(subset)),
                "total_positives": total_positives,
                "true_positives_at_n": true_positives_at_n,
                "precision_at_n": precision_at_n,
                "recall_at_n": recall_at_n,
            }
        )

    return rows


def evaluate_selected_threshold(
    df: pd.DataFrame,
    dataset_name: str,
    split_name: str,
    target_column: str,
    score_column: str,
    threshold: float,
) -> dict[str, Any]:
    subset = df[df["split"] == split_name].copy()

    y_true = subset[target_column].astype(int)
    y_pred = (subset[score_column] >= threshold).astype(int)

    counts = confusion_counts(y_true, y_pred)
    metrics = metrics_from_counts(counts)

    return {
        "dataset": dataset_name,
        "split": split_name,
        "selected_threshold": threshold,
        "records": int(len(subset)),
        "positives": int(y_true.sum()),
        "negatives": int((y_true == 0).sum()),
        **metrics,
    }


def load_dataset(path: Path, target_column: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    required_columns = ["annotation_id", "url", "title", "text_full", "split", target_column]
    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing columns in {path}: {missing_columns}")

    score_column = get_score_column(df)
    df[score_column] = pd.to_numeric(df[score_column], errors="coerce")

    missing_scores = int(df[score_column].isna().sum())
    if missing_scores:
        raise ValueError(f"{path} has {missing_scores} missing scores in {score_column}")

    return df


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Score Baseline Evaluation",
        "",
        "## Method",
        "",
        "The existing thematic score is evaluated as a threshold based classifier.",
        "Thresholds are explored on the train split.",
        "The best threshold is selected by train F1, with recall and precision as tie breakers.",
        "Final selected threshold metrics are reported on the test split.",
        "",
        "## Selected thresholds",
        "",
    ]

    for dataset_name, info in report["selected_thresholds"].items():
        lines.append(f"* {dataset_name}: `{info['threshold']}`")

    lines.extend(
        [
            "",
            "## Test metrics at selected thresholds",
            "",
        ]
    )

    for row in report["selected_threshold_test_metrics"]:
        lines.extend(
            [
                f"### {row['dataset']}",
                "",
                f"* Threshold: `{row['selected_threshold']}`",
                f"* Records: `{row['records']}`",
                f"* Positives: `{row['positives']}`",
                f"* Negatives: `{row['negatives']}`",
                f"* TP: `{row['tp']}`",
                f"* FP: `{row['fp']}`",
                f"* TN: `{row['tn']}`",
                f"* FN: `{row['fn']}`",
                f"* Precision: `{row['precision']:.3f}`",
                f"* Recall: `{row['recall']:.3f}`",
                f"* F1: `{row['f1']:.3f}`",
                f"* Accuracy: `{row['accuracy']:.3f}`",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate existing thematic score baseline on frozen evaluation datasets."
    )
    parser.add_argument(
        "--strict",
        default="data/annotation/evaluation/strict_binary_dataset.csv",
        help="Strict binary evaluation dataset.",
    )
    parser.add_argument(
        "--actionable",
        default="data/annotation/evaluation/actionable_binary_dataset.csv",
        help="Actionable binary evaluation dataset.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/evaluation/score_baseline",
        help="Output directory.",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "strict_binary": {
            "path": Path(args.strict),
            "target_column": "target_strict_relevant",
        },
        "actionable_binary": {
            "path": Path(args.actionable),
            "target_column": "target_actionable",
        },
    }

    threshold_rows: list[dict[str, Any]] = []
    at_n_rows: list[dict[str, Any]] = []
    selected_thresholds: dict[str, dict[str, Any]] = {}
    selected_threshold_test_metrics: list[dict[str, Any]] = []

    for dataset_name, config in datasets.items():
        df = load_dataset(config["path"], config["target_column"])
        score_column = get_score_column(df)

        for split_name in ["train", "test"]:
            threshold_rows.extend(
                evaluate_thresholds(
                    df=df,
                    dataset_name=dataset_name,
                    split_name=split_name,
                    target_column=config["target_column"],
                    score_column=score_column,
                )
            )
            at_n_rows.extend(
                evaluate_at_n(
                    df=df,
                    dataset_name=dataset_name,
                    split_name=split_name,
                    target_column=config["target_column"],
                    score_column=score_column,
                )
            )

        selected_threshold = select_best_threshold(threshold_rows, dataset_name)

        selected_thresholds[dataset_name] = {
            "threshold": selected_threshold,
            "selection_metric": "train_f1",
            "score_column": score_column,
        }

        selected_threshold_test_metrics.append(
            evaluate_selected_threshold(
                df=df,
                dataset_name=dataset_name,
                split_name="test",
                target_column=config["target_column"],
                score_column=score_column,
                threshold=selected_threshold,
            )
        )

    threshold_report = pd.DataFrame(threshold_rows)
    at_n_report = pd.DataFrame(at_n_rows)

    threshold_report_path = output_dir / "score_baseline_threshold_report.csv"
    at_n_report_path = output_dir / "score_baseline_at_n_report.csv"
    selected_thresholds_path = output_dir / "score_baseline_selected_thresholds.json"
    report_json_path = output_dir / "score_baseline_report.json"
    report_md_path = output_dir / "score_baseline_report.md"

    threshold_report.to_csv(threshold_report_path, index=False, encoding="utf-8")
    at_n_report.to_csv(at_n_report_path, index=False, encoding="utf-8")

    write_json(selected_thresholds_path, selected_thresholds)

    report = {
        "datasets": {
            name: {
                "path": str(config["path"]),
                "target_column": config["target_column"],
            }
            for name, config in datasets.items()
        },
        "thresholds": THRESHOLDS,
        "at_n_values": AT_N_VALUES,
        "selected_thresholds": selected_thresholds,
        "selected_threshold_test_metrics": selected_threshold_test_metrics,
        "outputs": {
            "threshold_report": str(threshold_report_path),
            "at_n_report": str(at_n_report_path),
            "selected_thresholds": str(selected_thresholds_path),
            "report_json": str(report_json_path),
            "report_md": str(report_md_path),
        },
    }

    write_json(report_json_path, report)
    report_md_path.write_text(build_markdown_report(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
