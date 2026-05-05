from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def infer_canton(source_id: str) -> str:
    source_id = source_id.strip().lower()

    if "_" not in source_id:
        return ""

    return source_id.split("_", 1)[0]


def value_counts_dict(series: pd.Series) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in series.value_counts(dropna=False).to_dict().items()
    }


def crosstab_dict(df: pd.DataFrame, index: str, columns: str) -> dict[str, dict[str, int]]:
    table = pd.crosstab(df[index], df[columns], dropna=False)

    result: dict[str, dict[str, int]] = {}

    for row_key, row in table.iterrows():
        result[str(row_key)] = {
            str(column_key): int(value)
            for column_key, value in row.to_dict().items()
        }

    return result


def numeric_summary_by_group(
    df: pd.DataFrame,
    group_column: str,
    value_column: str,
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}

    grouped = df.groupby(group_column, dropna=False)[value_column]

    for group, values in grouped:
        result[str(group)] = {
            "count": int(values.count()),
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": float(values.mean()),
            "median": float(values.median()),
        }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create quality and distribution report for the expanded annotation dataset."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Expanded annotation dataset CSV path.",
    )
    parser.add_argument(
        "--output-json",
        required=True,
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--output-md",
        required=True,
        help="Output Markdown report path.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_json_path = Path(args.output_json)
    output_md_path = Path(args.output_md)

    df = pd.read_csv(input_path)

    required_columns = [
        "url",
        "title",
        "text_full",
        "tlm_relevant",
        "review_required",
        "change_type",
        "notes",
        "triage_class",
        "source_file",
        "source_id",
        "text_hash",
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    for column in ["url", "title", "text_full", "notes", "source_file", "source_id"]:
        df[column] = df[column].apply(normalize_text)

    df["canton"] = df["source_id"].apply(infer_canton)
    df["text_length"] = df["text_full"].str.len()
    df["notes_length"] = df["notes"].str.len()

    invalid_true_review = df[
        (df["tlm_relevant"] == True) & (df["review_required"] == True)
    ]

    empty_notes = df[df["notes"] == ""]
    empty_text = df[df["text_full"] == ""]
    duplicate_urls = df[df.duplicated(subset=["url"], keep=False)]
    duplicate_texts = df[df.duplicated(subset=["text_hash"], keep=False)]

    report = {
        "input_path": str(input_path),
        "row_count": int(len(df)),
        "quality_checks": {
            "invalid_true_review_count": int(len(invalid_true_review)),
            "empty_notes_count": int(len(empty_notes)),
            "empty_text_count": int(len(empty_text)),
            "duplicate_url_rows": int(len(duplicate_urls)),
            "duplicate_text_hash_rows": int(len(duplicate_texts)),
        },
        "source_file_counts": value_counts_dict(df["source_file"]),
        "source_id_counts": value_counts_dict(df["source_id"]),
        "canton_counts": value_counts_dict(df["canton"]),
        "tlm_relevant_counts": value_counts_dict(df["tlm_relevant"]),
        "review_required_counts": value_counts_dict(df["review_required"]),
        "change_type_counts": value_counts_dict(df["change_type"]),
        "triage_class_counts": value_counts_dict(df["triage_class"]),
        "tlm_relevant_by_review_required": crosstab_dict(
            df,
            "tlm_relevant",
            "review_required",
        ),
        "triage_class_by_source_file": crosstab_dict(
            df,
            "source_file",
            "triage_class",
        ),
        "triage_class_by_canton": crosstab_dict(
            df,
            "canton",
            "triage_class",
        ),
        "triage_class_by_source_id": crosstab_dict(
            df,
            "source_id",
            "triage_class",
        ),
        "text_length_by_triage_class": numeric_summary_by_group(
            df,
            "triage_class",
            "text_length",
        ),
        "notes_length_by_triage_class": numeric_summary_by_group(
            df,
            "triage_class",
            "notes_length",
        ),
    }

    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        report["score_by_triage_class"] = numeric_summary_by_group(
            df.dropna(subset=["score"]),
            "triage_class",
            "score",
        )

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)

    with output_json_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")

    lines = [
        "# Annotation Dataset Quality Report",
        "",
        "## Input",
        "",
        f"* Input path: `{input_path}`",
        f"* Rows: `{len(df)}`",
        "",
        "## Quality checks",
        "",
    ]

    for key, value in report["quality_checks"].items():
        lines.append(f"* {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Triage class counts",
            "",
        ]
    )

    for key, value in report["triage_class_counts"].items():
        lines.append(f"* {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Label counts",
            "",
            "### tlm_relevant",
            "",
        ]
    )

    for key, value in report["tlm_relevant_counts"].items():
        lines.append(f"* {key}: `{value}`")

    lines.extend(
        [
            "",
            "### review_required",
            "",
        ]
    )

    for key, value in report["review_required_counts"].items():
        lines.append(f"* {key}: `{value}`")

    lines.extend(
        [
            "",
            "### change_type",
            "",
        ]
    )

    for key, value in report["change_type_counts"].items():
        lines.append(f"* {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Canton counts",
            "",
        ]
    )

    for key, value in report["canton_counts"].items():
        lines.append(f"* {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Source file counts",
            "",
        ]
    )

    for key, value in report["source_file_counts"].items():
        lines.append(f"* {key}: `{value}`")

    lines.append("")

    output_md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(report["quality_checks"], ensure_ascii=False, indent=2))
    print(f"Wrote JSON report: {output_json_path}")
    print(f"Wrote Markdown report: {output_md_path}")


if __name__ == "__main__":
    main()
