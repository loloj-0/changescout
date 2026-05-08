from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


OUTPUT_DIR = Path("results/evaluation/method_comparison")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def add_binary_row(
    rows: list[dict[str, Any]],
    method: str,
    dataset: str,
    metrics: dict[str, Any],
    method_type: str,
) -> None:
    rows.append(
        {
            "method": method,
            "method_type": method_type,
            "dataset": dataset,
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1": metrics.get("f1"),
            "accuracy": metrics.get("accuracy"),
            "tp": metrics.get("tp"),
            "fp": metrics.get("fp"),
            "tn": metrics.get("tn"),
            "fn": metrics.get("fn"),
        }
    )


def collect_score_baseline(rows: list[dict[str, Any]]) -> None:
    path = Path("results/evaluation/score_baseline/score_baseline_report.json")
    report = load_json(path)

    for metrics in report.get("selected_threshold_test_metrics", []):
        add_binary_row(
            rows=rows,
            method="thematic_score",
            dataset=metrics["dataset"],
            metrics=metrics,
            method_type="deterministic_score",
        )


def collect_classical_classifier(rows: list[dict[str, Any]]) -> None:
    path = Path("results/evaluation/classical_text_classifier/classical_text_classifier_metrics.json")
    report = load_json(path)

    for dataset, metrics in report.get("classifier_metrics", {}).items():
        converted = {
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1": metrics.get("f1"),
            "accuracy": metrics.get("accuracy"),
            "tp": metrics.get("tp"),
            "fp": metrics.get("fp"),
            "tn": metrics.get("tn"),
            "fn": metrics.get("fn"),
        }

        add_binary_row(
            rows=rows,
            method="tfidf_logistic_regression",
            dataset=dataset,
            metrics=converted,
            method_type="classical_ml",
        )


def collect_llm_reports(rows: list[dict[str, Any]]) -> None:
    root = Path("results/evaluation/local_llm")

    for path in sorted(root.glob("*/*/llm_triage_evaluation_report.json")):
        report = load_json(path)
        model_id = report.get("model_id", "")
        prompt_variant = report.get("prompt_variant", "")
        method = f"{model_id} [{prompt_variant}]"

        for dataset in ["strict_binary", "actionable_binary"]:
            add_binary_row(
                rows=rows,
                method=method,
                dataset=dataset,
                metrics=report.get(dataset, {}),
                method_type="local_llm",
            )


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# ChangeScout Method Comparison",
        "",
        "## Binary evaluation",
        "",
        "| Dataset | Method | Type | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    ordered = df.sort_values(["dataset", "f1", "recall"], ascending=[True, False, False])

    for _, row in ordered.iterrows():
        lines.append(
            "| "
            f"{row['dataset']} | "
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
            "The TF IDF Logistic Regression classifier is the strongest method on both strict binary relevance and actionable lead detection.",
            "The local LLMs produce valid structured outputs and high precision, but their recall is lower than the deterministic score baseline and the classical classifier.",
            "Qwen 14B improves actionable lead detection compared with smaller local LLMs, mainly by assigning many confirmed relevant cases to needs_review rather than not_relevant.",
            "For ChangeScout, the most plausible role of local LLMs is not standalone lead discovery, but hybrid review support, precision filtering, and evidence generation.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    rows: list[dict[str, Any]] = []

    collect_score_baseline(rows)
    collect_classical_classifier(rows)
    collect_llm_reports(rows)

    df = pd.DataFrame(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_csv = OUTPUT_DIR / "method_comparison_binary.csv"
    output_json = OUTPUT_DIR / "method_comparison_binary.json"
    output_md = OUTPUT_DIR / "method_comparison_binary.md"

    df.to_csv(output_csv, index=False, encoding="utf-8")
    output_json.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(build_markdown(df), encoding="utf-8")

    print(f"Wrote {output_csv}")
    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")
    print()
    print(df.sort_values(["dataset", "f1", "recall"], ascending=[True, False, False]).to_string(index=False))


if __name__ == "__main__":
    main()
