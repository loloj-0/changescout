import json
from pathlib import Path

import pandas as pd


def fix_encoding(text):
    if not text:
        return text

    try:
        return text.encode("cp1252").decode("utf-8")
    except Exception:
        return text


def normalize_text(text):
    if not text:
        return text

    text = fix_encoding(text)

    text = text.replace("–", " ")
    text = text.replace("—", " ")
    text = text.replace("\xa0", " ")

    return text.strip()


def export_jsonl_to_excel(input_path: str, output_path: str) -> None:
    rows = []

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)

            title = normalize_text(record.get("title"))
            clean_text = normalize_text(record.get("clean_text") or "")

            rows.append(
                {
                    "url": record.get("url"),
                    "title": title,
                    "score": round(record.get("thematic_score", 0), 3),
                    "source_id": record.get("source_id"),
                    "text_preview": clean_text[:500],
                    "tlm_relevant": "",
                    "review_required": "",
                    "change_type": "",
                    "notes": ""
                }
            )

    df = pd.DataFrame(rows)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output, index=False)

    print(f"written: {output}")


if __name__ == "__main__":
    export_jsonl_to_excel(
        input_path="data/annotation/candidates/expansion_full_131_sorted_clean.jsonl",
        output_path="data/annotation/expansion_full_131.xlsx",
    )