from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split


VALID_TRIAGE_CLASSES = {
    "confirmed_relevant",
    "needs_review",
    "not_relevant",
}


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def value_counts_dict(series: pd.Series) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in series.value_counts(dropna=False).to_dict().items()
    }


def add_split_column(
    df: pd.DataFrame,
    stratify_column: str,
    test_size: float,
    random_state: int,
) -> pd.DataFrame:
    result = df.copy()

    if len(result) == 0:
        raise ValueError("Cannot split empty dataset")

    train_index, test_index = train_test_split(
        result.index,
        test_size=test_size,
        random_state=random_state,
        stratify=result[stratify_column],
    )

    result["split"] = "train"
    result.loc[test_index, "split"] = "test"

    return result


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Dataset Report",
        "",
        "## Input",
        "",
        f"* Input path: `{report['input_path']}`",
        f"* Input rows: `{report['input_rows']}`",
        f"* Test size: `{report['test_size']}`",
        f"* Random state: `{report['random_state']}`",
        "",
        "## Outputs",
        "",
    ]

    for name, info in report["datasets"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"* Path: `{info['path']}`",
                f"* Rows: `{info['rows']}`",
                f"* Target column: `{info['target_column']}`",
                f"* Split column: `split`",
                "",
                "Class counts:",
                "",
            ]
        )

        for key, value in info["class_counts"].items():
            lines.append(f"* {key}: `{value}`")

        lines.extend(
            [
                "",
                "Split counts:",
                "",
            ]
        )

        for key, value in info["split_counts"].items():
            lines.append(f"* {key}: `{value}`")

        lines.append("")

    lines.extend(
        [
            "## Label mapping",
            "",
            "### strict_binary",
            "",
            "* confirmed_relevant -> 1",
            "* not_relevant -> 0",
            "* needs_review -> excluded",
            "",
            "### actionable_binary",
            "",
            "* confirmed_relevant -> 1",
            "* needs_review -> 1",
            "* not_relevant -> 0",
            "",
            "### triage_3class",
            "",
            "* confirmed_relevant",
            "* needs_review",
            "* not_relevant",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build evaluation datasets from the frozen expanded annotation dataset."
    )
    parser.add_argument(
        "--input",
        default="data/annotation/labeled/annotation_dataset_expanded.csv",
        help="Frozen expanded annotation dataset CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/annotation/evaluation",
        help="Output directory for evaluation datasets.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Stratified test split size.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible splits.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    strict_path = output_dir / "strict_binary_dataset.csv"
    actionable_path = output_dir / "actionable_binary_dataset.csv"
    triage_path = output_dir / "triage_3class_dataset.csv"
    report_json_path = output_dir / "evaluation_dataset_report.json"
    report_md_path = output_dir / "evaluation_dataset_report.md"

    df = pd.read_csv(input_path)

    required_columns = [
        "annotation_id",
        "url",
        "source_id",
        "title",
        "text_full",
        "tlm_relevant",
        "review_required",
        "change_type",
        "notes",
        "triage_class",
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    for column in ["annotation_id", "url", "source_id", "title", "text_full", "notes", "triage_class"]:
        df[column] = df[column].apply(normalize_text)

    invalid_classes = sorted(set(df["triage_class"]) - VALID_TRIAGE_CLASSES)
    if invalid_classes:
        raise ValueError(f"Invalid triage_class values: {invalid_classes}")

    invalid_true_review = df[
        (df["tlm_relevant"] == True) & (df["review_required"] == True)
    ]
    if len(invalid_true_review) > 0:
        raise ValueError(f"Invalid true plus review rows: {len(invalid_true_review)}")

    output_dir.mkdir(parents=True, exist_ok=True)

    strict = df[df["triage_class"].isin(["confirmed_relevant", "not_relevant"])].copy()
    strict["target_strict_relevant"] = (
        strict["triage_class"] == "confirmed_relevant"
    ).astype(int)
    strict = add_split_column(
        strict,
        stratify_column="target_strict_relevant",
        test_size=args.test_size,
        random_state=args.random_state,
    )

    actionable = df.copy()
    actionable["target_actionable"] = (
        actionable["triage_class"].isin(["confirmed_relevant", "needs_review"])
    ).astype(int)
    actionable = add_split_column(
        actionable,
        stratify_column="target_actionable",
        test_size=args.test_size,
        random_state=args.random_state,
    )

    triage = df.copy()
    triage["target_triage_class"] = triage["triage_class"]
    triage = add_split_column(
        triage,
        stratify_column="target_triage_class",
        test_size=args.test_size,
        random_state=args.random_state,
    )

    strict.to_csv(strict_path, index=False, encoding="utf-8")
    actionable.to_csv(actionable_path, index=False, encoding="utf-8")
    triage.to_csv(triage_path, index=False, encoding="utf-8")

    report = {
        "input_path": str(input_path),
        "input_rows": int(len(df)),
        "test_size": args.test_size,
        "random_state": args.random_state,
        "datasets": {
            "strict_binary": {
                "path": str(strict_path),
                "rows": int(len(strict)),
                "target_column": "target_strict_relevant",
                "class_counts": value_counts_dict(strict["target_strict_relevant"]),
                "split_counts": value_counts_dict(strict["split"]),
                "triage_class_counts": value_counts_dict(strict["triage_class"]),
            },
            "actionable_binary": {
                "path": str(actionable_path),
                "rows": int(len(actionable)),
                "target_column": "target_actionable",
                "class_counts": value_counts_dict(actionable["target_actionable"]),
                "split_counts": value_counts_dict(actionable["split"]),
                "triage_class_counts": value_counts_dict(actionable["triage_class"]),
            },
            "triage_3class": {
                "path": str(triage_path),
                "rows": int(len(triage)),
                "target_column": "target_triage_class",
                "class_counts": value_counts_dict(triage["target_triage_class"]),
                "split_counts": value_counts_dict(triage["split"]),
                "triage_class_counts": value_counts_dict(triage["triage_class"]),
            },
        },
    }

    write_json(report_json_path, report)
    report_md_path.write_text(build_markdown_report(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote strict binary dataset: {strict_path}")
    print(f"Wrote actionable binary dataset: {actionable_path}")
    print(f"Wrote triage 3class dataset: {triage_path}")
    print(f"Wrote report JSON: {report_json_path}")
    print(f"Wrote report Markdown: {report_md_path}")


if __name__ == "__main__":
    main()
