import argparse
import json
from pathlib import Path


REPLACEMENTS = {
    "Ã¤": "ä",
    "Ã¶": "ö",
    "Ã¼": "ü",
    "Ã„": "Ä",
    "Ã–": "Ö",
    "Ãœ": "Ü",
    "Ã©": "é",
    "Ãè": "è",
    "Ãè": "è",
    "Ã¨": "è",
    "Ãffentliche": "Öffentliche",
    "Ãffentlich": "Öffentlich",
    "â¢": "•",
    "â¢": "•",
    "â": " ",
    "â€“": " ",
    "â": " ",
    "â€œ": "\"",
    "â€": "\"",
    "â": "\"",
    "â": "\"",
    "â€™": "'",
    "â": "'",
    "Â": "",
    "\u00e2\u0080\u00a6": "...",
    "â¦": "...",
    "\u00c3\u00a4": "ä",
    "\u00c3\u00b6": "ö",
    "\u00c3\u00bc": "ü",
    "\u00c3\u0084": "Ä",
    "\u00c3\u0096": "Ö",
    "\u00c3\u009c": "Ü",
    "\u00c3\u00a9": "é",
    "\u00c3\u00a8": "è",
    "\u00e2\u0080\u00a2": "•",
    "\u00e2\u0080\u0093": " ",
    "\u00e2\u0080\u0094": " ",
    "\u00e2\u0080\u009c": "\"",
    "\u00e2\u0080\u009d": "\"",
    "\u00e2\u0080\u0099": "'",
    "\u00c2": "",
}

BAD_TOKENS = ["Ã", "Â", "â", "�", "\u0080", "\u0093", "\u0094", "\u0096", "\u009c", "\u009d"]


def fix_text(text):
    if not isinstance(text, str):
        return text

    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)

    text = text.replace("–", " ")
    text = text.replace("—", " ")
    text = text.replace("\xa0", " ")

    return " ".join(text.split())


def fix_value(value):
    if isinstance(value, str):
        return fix_text(value)

    if isinstance(value, list):
        return [fix_value(item) for item in value]

    if isinstance(value, dict):
        return {key: fix_value(val) for key, val in value.items()}

    return value


def validate(records):
    broken = 0

    for i, record in enumerate(records, start=1):
        text = (record.get("title") or "") + " " + (record.get("clean_text") or "")
        hits = [token for token in BAD_TOKENS if token in text]

        if hits:
            broken += 1
            print(f"[BROKEN] line={i} title={record.get('title')} hits={hits}")
            print(repr(text[:500]))

    print()
    print("Validation result:")
    print(f"total_records={len(records)}")
    print(f"broken_records={broken}")

    return broken


def repair_jsonl(input_path, output_path):
    records = []

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            records.append(fix_value(json.loads(line)))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"written: {output}")

    broken = validate(records)

    if broken > 0:
        print("WARNING: Encoding issues still present")
    else:
        print("OK: No encoding issues found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repair_jsonl(args.input, args.output)