import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List


REPLACEMENTS = {
    "Ã¤": "ä",
    "Ã¶": "ö",
    "Ã¼": "ü",
    "Ã„": "Ä",
    "Ã–": "Ö",
    "Ãœ": "Ü",
    "Ã©": "é",
    "Ã¨": "è",
    "Ãª": "ê",
    "Ã«": "ë",
    "Ã ": "à",
    "Ã¡": "á",
    "Ã¢": "â",
    "Ã§": "ç",
    "Ã±": "ñ",
    "Ãffentliche": "Öffentliche",
    "Ãffentlich": "Öffentlich",
    "Ã–ffentliche": "Öffentliche",
    "Ã–ffentlich": "Öffentlich",
    "â¢": "•",
    "â¢": "•",
    "â": " ",
    "â€“": " ",
    "â": " ",
    "â€œ": '"',
    "â€": '"',
    "â": '"',
    "â": '"',
    "â€™": "'",
    "â": "'",
    "â¦": "...",
    "Â": "",
    "\u00c3\u00a4": "ä",
    "\u00c3\u00b6": "ö",
    "\u00c3\u00bc": "ü",
    "\u00c3\u0084": "Ä",
    "\u00c3\u0096": "Ö",
    "\u00c3\u009c": "Ü",
    "\u00c3\u00a9": "é",
    "\u00c3\u00a8": "è",
    "\u00c3\u00aa": "ê",
    "\u00c3\u00ab": "ë",
    "\u00c3\u00a0": "à",
    "\u00c3\u00a1": "á",
    "\u00c3\u00a2": "â",
    "\u00c3\u00a7": "ç",
    "\u00c3\u00b1": "ñ",
    "\u00e2\u0080\u00a2": "•",
    "\u00e2\u0080\u0093": " ",
    "\u00e2\u0080\u0094": " ",
    "\u00e2\u0080\u009c": '"',
    "\u00e2\u0080\u009d": '"',
    "\u00e2\u0080\u0099": "'",
    "\u00e2\u0080\u00a6": "...",
    "\u00c2": "",
}

BAD_TOKENS = [
    "Ã",
    "Â",
    "â",
    "�",
    "\u0080",
    "\u0093",
    "\u0094",
    "\u0096",
    "\u009c",
    "\u009d",
]


def apply_replacements(text: str) -> str:
    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)

    return text


def normalize_whitespace_preserve_paragraphs(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")
    text = text.replace("–", " ")
    text = text.replace("—", " ")

    normalized_lines: List[str] = []
    blank_pending = False

    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()

        if not line:
            if normalized_lines:
                blank_pending = True
            continue

        if blank_pending and normalized_lines and normalized_lines[-1] != "":
            normalized_lines.append("")

        normalized_lines.append(line)
        blank_pending = False

    result = "\n".join(normalized_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def fix_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text

    text = apply_replacements(text)
    text = normalize_whitespace_preserve_paragraphs(text)

    return text


def fix_value(value: Any) -> Any:
    if isinstance(value, str):
        return fix_text(value)

    if isinstance(value, list):
        return [fix_value(item) for item in value]

    if isinstance(value, dict):
        return {key: fix_value(val) for key, val in value.items()}

    return value


def load_jsonl(input_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at line {line_number} in {input_path}") from error

            if not isinstance(record, dict):
                raise ValueError(f"Expected JSON object at line {line_number} in {input_path}")

            records.append(record)

    return records


def write_jsonl(output_path: Path, records: List[Dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def validate(records: List[Dict[str, Any]]) -> int:
    broken = 0

    fields_to_check = [
        "title",
        "clean_text",
        "text_full",
        "notes",
    ]

    for index, record in enumerate(records, start=1):
        text_parts = []

        for field in fields_to_check:
            value = record.get(field)
            if isinstance(value, str):
                text_parts.append(value)

        combined_text = " ".join(text_parts)
        hits = [token for token in BAD_TOKENS if token in combined_text]

        if hits:
            broken += 1
            print(f"[BROKEN] line={index} title={record.get('title')} hits={hits}")
            print(repr(combined_text[:500]))

    print()
    print("Validation result:")
    print(f"total_records={len(records)}")
    print(f"broken_records={broken}")

    return broken


def repair_jsonl(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    records = load_jsonl(input_file)
    repaired_records = [fix_value(record) for record in records]

    write_jsonl(output_file, repaired_records)

    print(f"input: {input_file}")
    print(f"records: {len(repaired_records)}")
    print(f"written: {output_file}")

    broken = validate(repaired_records)

    if broken > 0:
        print("WARNING: Encoding issues still present")
    else:
        print("OK: No encoding issues found")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair mojibake encoding issues in JSONL annotation candidates."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSONL file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output repaired JSONL file.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    repair_jsonl(
        input_path=args.input,
        output_path=args.output,
    )