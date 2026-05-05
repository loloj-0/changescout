from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def collect_reports(root: Path) -> list[Path]:
    return sorted(root.glob("*/*/llm_triage_evaluation_report.json"))


def report_to_row(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    strict = report.get("strict_binary", {})
    actionable = report.get("actionable_binary", {})
    triage = report.get("triage_3class", {})

    return {
        "model_id": report.get("model_id", ""),
        "prompt_variant": report.get("prompt_variant", ""),
        "records": report.get("records", 0),
        "parse_success_rate": report.get("parse_success_rate", 0.0),
        "strict_precision": strict.get("precision", 0.0),
        "strict_recall": strict.get("recall", 0.0),
        "strict_f1": strict.get("f1", 0.0),
        "strict_tp": strict.get("tp", 0),
        "strict_fp": strict.get("fp", 0),
        "strict_tn": strict.get("tn", 0),
        "strict_fn": strict.get("fn", 0),
        "actionable_precision": actionable.get("precision", 0.0),
        "actionable_recall": actionable.get("recall", 0.0),
        "actionable_f1": actionable.get("f1", 0.0),
        "actionable_tp": actionable.get("tp", 0),
        "actionable_fp": actionable.get("fp", 0),
        "actionable_tn": actionable.get("tn", 0),
        "actionable_fn": actionable.get("fn", 0),
        "triage_accuracy": triage.get("accuracy", 0.0),
        "report_path": str(path),
    }


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Local LLM Comparison",
        "",
        "## Summary",
        "",
        "| Model | Prompt | Parse | Strict P | Strict R | Strict F1 | Actionable P | Actionable R | Actionable F1 | Triage Acc |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for _, row in df.sort_values(
        ["actionable_f1", "strict_f1"],
        ascending=False,
    ).iterrows():
        lines.append(
            "| "
            f"{row['model_id']} | "
            f"{row['prompt_variant']} | "
            f"{row['parse_success_rate']:.3f} | "
            f"{row['strict_precision']:.3f} | "
            f"{row['strict_recall']:.3f} | "
            f"{row['strict_f1']:.3f} | "
            f"{row['actionable_precision']:.3f} | "
            f"{row['actionable_recall']:.3f} | "
            f"{row['actionable_f1']:.3f} | "
            f"{row['triage_accuracy']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "All local LLMs were evaluated on the frozen triage test split.",
            "Strict binary and actionable binary metrics are derived from the same triage predictions.",
            "For ChangeScout, actionable recall and actionable F1 are more relevant than global accuracy because the workflow is lead prioritization with human review.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare all local LLM evaluation reports."
    )
    parser.add_argument(
        "--input-root",
        default="data/annotation/evaluation/local_llm",
    )
    parser.add_argument(
        "--output-dir",
        default="data/annotation/evaluation/local_llm/comparison",
    )

    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for report_path in collect_reports(input_root):
        report = load_json(report_path)
        rows.append(report_to_row(report_path, report))

    if not rows:
        raise FileNotFoundError(f"No LLM evaluation reports found under {input_root}")

    df = pd.DataFrame(rows)

    output_csv = output_dir / "local_llm_comparison.csv"
    output_md = output_dir / "local_llm_comparison.md"
    output_json = output_dir / "local_llm_comparison.json"

    df.to_csv(output_csv, index=False, encoding="utf-8")

    output_json.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    output_md.write_text(build_markdown(df), encoding="utf-8")

    print(f"Wrote {output_csv}")
    print(f"Wrote {output_md}")
    print(f"Wrote {output_json}")
    print()
    print(
        df.sort_values(
            ["actionable_f1", "strict_f1"],
            ascending=False,
        ).to_string(index=False)
    )


if __name__ == "__main__":
    main()
