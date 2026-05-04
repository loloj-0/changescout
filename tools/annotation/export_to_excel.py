import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def fix_encoding(text: Optional[str]) -> Optional[str]:
    if not text:
        return text

    try:
        return text.encode("cp1252").decode("utf-8")
    except Exception:
        return text


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""

    fixed = fix_encoding(text)
    if not fixed:
        return ""

    fixed = fixed.replace("–", " ")
    fixed = fixed.replace("—", " ")
    fixed = fixed.replace("\xa0", " ")

    return fixed.strip()


def load_jsonl(input_path: str) -> List[Dict[str, Any]]:
    records = []

    with open(input_path, encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "Invalid JSON at line {} in {}".format(line_number, input_path)
                ) from error

            if not isinstance(record, dict):
                raise ValueError(
                    "Expected JSON object at line {} in {}".format(line_number, input_path)
                )

            records.append(record)

    return records


def get_score(record: Dict[str, Any]) -> float:
    value = record.get("thematic_score", record.get("score", 0))

    if value is None:
        return 0.0

    try:
        return round(float(value), 3)
    except (ValueError, TypeError):
        return 0.0


def build_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []

    for record in records:
        rows.append(
            {
                "url": record.get("url"),
                "title": normalize_text(record.get("title")),
                "score": get_score(record),
                "source_id": record.get("source_id"),
                "text_full": normalize_text(
                    record.get("clean_text") or record.get("text_full") or ""
                ),
                "tlm_relevant": "",
                "review_required": "",
                "change_type": "",
                "notes": "",
            }
        )

    return rows


def export_jsonl_to_excel(input_path: str, output_path: str) -> None:
    records = load_jsonl(input_path)
    rows = build_rows(records)

    df = pd.DataFrame(rows)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(output, index=False)

    print("input: {}".format(input_path))
    print("records: {}".format(len(records)))
    print("written: {}".format(output))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export scored annotation candidates from JSONL to Excel."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input scored JSONL file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output Excel file.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    export_jsonl_to_excel(
        input_path=args.input,
        output_path=args.output,
    )