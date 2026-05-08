from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score


TRIAGE_LABELS = [
    "confirmed_relevant",
    "needs_review",
    "not_relevant",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def binary_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict[str, Any]:
    labels = [0, 1]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=labels).ravel()

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


def evaluate_strict(df: pd.DataFrame) -> dict[str, Any]:
    subset = df[df["gold_triage_class"].isin(["confirmed_relevant", "not_relevant"])].copy()

    y_true = (subset["gold_triage_class"] == "confirmed_relevant").astype(int)
    y_pred = (subset["triage_class"] == "confirmed_relevant").astype(int)

    return binary_metrics(y_true, y_pred)


def evaluate_actionable(df: pd.DataFrame) -> dict[str, Any]:
    subset = df.copy()

    y_true = (subset["gold_triage_class"].isin(["confirmed_relevant", "needs_review"])).astype(int)
    y_pred = (subset["triage_class"].isin(["confirmed_relevant", "needs_review"])).astype(int)

    return binary_metrics(y_true, y_pred)


def evaluate_triage(df: pd.DataFrame) -> dict[str, Any]:
    y_true = df["gold_triage_class"].fillna("invalid").astype(str)
    y_pred = df["triage_class"].fillna("invalid").astype(str)

    labels = TRIAGE_LABELS + ["invalid"]

    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    return {
        "labels": labels,
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def load_baseline_reports() -> dict[str, Any]:
    baselines: dict[str, Any] = {}

    score_path = Path("data/annotation/evaluation/score_baseline/score_baseline_report.json")
    if score_path.exists():
        score = json.loads(score_path.read_text(encoding="utf-8"))
        baselines["score_baseline"] = {
            row["dataset"]: row
            for row in score.get("selected_threshold_test_metrics", [])
        }

    clf_path = Path("data/annotation/evaluation/classical_text_classifier/classical_text_classifier_metrics.json")
    if clf_path.exists():
        clf = json.loads(clf_path.read_text(encoding="utf-8"))
        baselines["classical_text_classifier"] = clf.get("classifier_metrics", {})

    return baselines


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Local LLM Triage Evaluation",
        "",
        f"* Model: `{report['model_id']}`",
        f"* Prompt variant: `{report['prompt_variant']}`",
        f"* Records: `{report['records']}`",
        f"* Parse success rate: `{report['parse_success_rate']:.3f}`",
        "",
        "## Binary metrics",
        "",
    ]

    for name in ["strict_binary", "actionable_binary"]:
        metrics = report[name]
        lines.extend(
            [
                f"### {name}",
                "",
                f"* Records: `{metrics['records']}`",
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
            "## Three class triage",
            "",
            f"* Accuracy: `{report['triage_3class']['accuracy']:.3f}`",
            "",
            "Labels:",
            "",
        ]
    )

    for label in report["triage_3class"]["labels"]:
        lines.append(f"* `{label}`")

    lines.extend(
        [
            "",
            "Confusion matrix rows are gold labels, columns are predicted labels.",
            "",
            "```text",
        ]
    )

    for row in report["triage_3class"]["confusion_matrix"]:
        lines.append(str(row))

    lines.extend(
        [
            "```",
            "",
            "## Baseline comparison",
            "",
        ]
    )

    baselines = report.get("baselines", {})

    for baseline_name, baseline_data in baselines.items():
        lines.append(f"### {baseline_name}")
        lines.append("")

        for dataset_name, metrics in baseline_data.items():
            if dataset_name not in ["strict_binary", "actionable_binary"]:
                continue

            lines.append(
                f"* {dataset_name}: precision `{metrics.get('precision', 0):.3f}`, "
                f"recall `{metrics.get('recall', 0):.3f}`, "
                f"F1 `{metrics.get('f1', 0):.3f}`"
            )

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate local LLM triage predictions."
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="LLM triage predictions JSONL.",
    )

    args = parser.parse_args()

    predictions_path = Path(args.predictions)
    output_dir = predictions_path.parent

    records = load_jsonl(predictions_path)
    df = pd.DataFrame(records)

    required_columns = [
        "model_id",
        "prompt_variant",
        "gold_triage_class",
        "triage_class",
        "parse_success",
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in predictions: {missing_columns}")

    parse_success_count = int(df["parse_success"].sum())
    parse_success_rate = parse_success_count / len(df) if len(df) else 0.0

    report = {
        "model_id": str(df["model_id"].iloc[0]) if len(df) else "",
        "prompt_variant": str(df["prompt_variant"].iloc[0]) if len(df) else "",
        "records": int(len(df)),
        "parse_success_count": parse_success_count,
        "parse_success_rate": parse_success_rate,
        "strict_binary": evaluate_strict(df),
        "actionable_binary": evaluate_actionable(df),
        "triage_3class": evaluate_triage(df),
        "baselines": load_baseline_reports(),
        "prediction_path": str(predictions_path),
    }

    report_json_path = output_dir / "llm_triage_evaluation_report.json"
    report_md_path = output_dir / "llm_triage_evaluation_report.md"

    write_json(report_json_path, report)
    report_md_path.write_text(build_markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
