from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


VALID_CHANGE_TYPES = {"topology", "geometry", "attribute_only", "none"}


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    text = normalize_text(value).lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n"}:
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def make_text_hash(value: Any) -> str:
    text = normalize_text(value)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_triage_class(tlm_relevant: bool, review_required: bool) -> str:
    if tlm_relevant and not review_required:
        return "confirmed_relevant"

    if not tlm_relevant and review_required:
        return "needs_review"

    if not tlm_relevant and not review_required:
        return "not_relevant"

    return "invalid"


def load_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_excel(path)
    df["source_file"] = path.name
    df["source_row"] = df.index + 2
    return df


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build expanded labeled annotation dataset from reviewed Excel files."
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Reviewed annotation Excel file. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-jsonl",
        required=True,
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--output-csv",
        required=True,
        help="Output CSV path.",
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Output report JSON path.",
    )
    parser.add_argument(
        "--duplicate-urls",
        required=True,
        help="Output CSV path for duplicate URLs before deduplication.",
    )
    parser.add_argument(
        "--duplicate-texts",
        required=True,
        help="Output CSV path for duplicate text hashes before deduplication.",
    )
    args = parser.parse_args()

    input_paths = [Path(path) for path in args.input]
    output_jsonl = Path(args.output_jsonl)
    output_csv = Path(args.output_csv)
    report_path = Path(args.report)
    duplicate_urls_path = Path(args.duplicate_urls)
    duplicate_texts_path = Path(args.duplicate_texts)

    frames = [load_excel(path) for path in input_paths]
    df = pd.concat(frames, ignore_index=True)

    required_columns = [
        "url",
        "title",
        "text_full",
        "tlm_relevant",
        "review_required",
        "change_type",
        "notes",
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["url"] = df["url"].apply(normalize_text)
    df["title"] = df["title"].apply(normalize_text)
    df["text_full"] = df["text_full"].apply(normalize_text)
    df["notes"] = df["notes"].apply(normalize_text)
    df["change_type"] = df["change_type"].apply(normalize_text)

    df["tlm_relevant"] = df["tlm_relevant"].apply(normalize_bool)
    df["review_required"] = df["review_required"].apply(normalize_bool)

    df["text_hash"] = df["text_full"].apply(make_text_hash)
    df["triage_class"] = [
        derive_triage_class(tlm_relevant, review_required)
        for tlm_relevant, review_required in zip(df["tlm_relevant"], df["review_required"])
    ]

    invalid_change_types = sorted(set(df["change_type"]) - VALID_CHANGE_TYPES)
    if invalid_change_types:
        raise ValueError(f"Invalid change_type values: {invalid_change_types}")

    invalid_triage = df[df["triage_class"] == "invalid"]
    if len(invalid_triage) > 0:
        details = invalid_triage[
            ["source_file", "source_row", "url", "tlm_relevant", "review_required"]
        ]
        raise ValueError(f"Invalid triage combinations:\n{details.to_string(index=False)}")

    empty_notes = df[df["notes"] == ""]
    if len(empty_notes) > 0:
        details = empty_notes[["source_file", "source_row", "url"]]
        raise ValueError(f"Rows with empty notes:\n{details.to_string(index=False)}")

    empty_text = df[df["text_full"] == ""]
    if len(empty_text) > 0:
        details = empty_text[["source_file", "source_row", "url"]]
        raise ValueError(f"Rows with empty text_full:\n{details.to_string(index=False)}")

    duplicate_urls = df[df.duplicated(subset=["url"], keep=False)].sort_values(
        ["url", "source_file", "source_row"]
    )
    duplicate_texts = df[df.duplicated(subset=["text_hash"], keep=False)].sort_values(
        ["text_hash", "source_file", "source_row"]
    )

    duplicate_urls_path.parent.mkdir(parents=True, exist_ok=True)
    duplicate_texts_path.parent.mkdir(parents=True, exist_ok=True)
    duplicate_urls.to_csv(duplicate_urls_path, index=False, encoding="utf-8")
    duplicate_texts.to_csv(duplicate_texts_path, index=False, encoding="utf-8")

    row_count_before_dedup = len(df)

    df = df.drop_duplicates(subset=["url"], keep="first").reset_index(drop=True)
    df["annotation_id"] = [f"ann_{index:04d}" for index in range(1, len(df) + 1)]

    records = df.to_dict(orient="records")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_csv, index=False, encoding="utf-8")
    write_jsonl(output_jsonl, records)

    report = {
        "input_files": [str(path) for path in input_paths],
        "row_count_before_dedup": int(row_count_before_dedup),
        "row_count_after_dedup": int(len(df)),
        "duplicate_url_rows_before_dedup": int(len(duplicate_urls)),
        "duplicate_text_hash_rows_before_dedup": int(len(duplicate_texts)),
        "source_file_counts": {
            str(key): int(value)
            for key, value in df["source_file"].value_counts(dropna=False).to_dict().items()
        },
        "tlm_relevant_counts": {
            str(key): int(value)
            for key, value in df["tlm_relevant"].value_counts(dropna=False).to_dict().items()
        },
        "review_required_counts": {
            str(key): int(value)
            for key, value in df["review_required"].value_counts(dropna=False).to_dict().items()
        },
        "change_type_counts": {
            str(key): int(value)
            for key, value in df["change_type"].value_counts(dropna=False).to_dict().items()
        },
        "triage_class_counts": {
            str(key): int(value)
            for key, value in df["triage_class"].value_counts(dropna=False).to_dict().items()
        },
    }

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
