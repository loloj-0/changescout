from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import re

import pandas as pd


REQUIRED_REFERENCE_COLUMNS = {
    "name",
    "hint_type",
    "canton",
    "source",
    "priority",
}

DEFAULT_MIN_NAME_LENGTH = 3


def load_location_reference(path: Path) -> pd.DataFrame:
    reference = pd.read_csv(path)

    missing_columns = REQUIRED_REFERENCE_COLUMNS - set(reference.columns)
    if missing_columns:
        raise ValueError(f"Missing reference columns: {sorted(missing_columns)}")

    reference = reference.copy()
    reference["name"] = reference["name"].astype(str).str.strip()
    reference["hint_type"] = reference["hint_type"].astype(str).str.strip()
    reference["canton"] = reference["canton"].fillna("").astype(str).str.strip()
    reference["source"] = reference["source"].astype(str).str.strip()
    reference["priority"] = reference["priority"].astype(int)

    reference = reference[reference["name"] != ""].copy()
    reference = reference.sort_values(
        by=["priority", "hint_type", "name", "canton"],
        ascending=[False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    return reference


def normalize_text(text: Any) -> str:
    if text is None:
        return ""

    normalized = " ".join(str(text).split())
    return normalized.casefold()


def build_name_pattern(name: str) -> re.Pattern[str]:
    escaped = re.escape(normalize_text(name))
    return re.compile(rf"(?<!\w){escaped}(?!\w)")


def count_name_matches(text: str, name: str) -> int:
    if not text or not name:
        return 0

    pattern = build_name_pattern(name)
    return len(pattern.findall(normalize_text(text)))


def find_location_hints_for_document(
    document: Dict[str, Any],
    reference: pd.DataFrame,
    min_name_length: int = DEFAULT_MIN_NAME_LENGTH,
) -> List[Dict[str, Any]]:
    title = str(document.get("title") or "")
    clean_text = str(document.get("clean_text") or "")

    hints: List[Dict[str, Any]] = []

    for row in reference.to_dict(orient="records"):
        name = str(row["name"]).strip()

        if len(name) < min_name_length:
            continue

        title_count = count_name_matches(title, name)
        text_count = count_name_matches(clean_text, name)
        total_count = title_count + text_count

        if total_count == 0:
            continue

        matched_fields = []
        if title_count:
            matched_fields.append("title")
        if text_count:
            matched_fields.append("clean_text")

        hints.append(
            {
                "hint_type": row["hint_type"],
                "name": name,
                "canton": row.get("canton", ""),
                "source": row.get("source", ""),
                "matched_fields": matched_fields,
                "match_count": total_count,
                "priority": int(row["priority"]),
            }
        )

    hints = sorted(
        hints,
        key=lambda hint: (
            -int(hint["priority"]),
            str(hint["hint_type"]),
            str(hint["name"]),
            str(hint.get("canton", "")),
        ),
    )

    return hints


def flatten_location_hints(hints: List[Dict[str, Any]]) -> Dict[str, Any]:
    hint_names = [hint["name"] for hint in hints]
    hint_types = [hint["hint_type"] for hint in hints]

    municipality_names = [
        hint["name"]
        for hint in hints
        if hint["hint_type"] == "municipality"
    ]

    geographic_names = [
        hint["name"]
        for hint in hints
        if hint["hint_type"] != "municipality"
    ]

    return {
        "location_hint_count": len(hints),
        "location_hint_names": "; ".join(hint_names),
        "location_hint_types": "; ".join(sorted(set(hint_types))),
        "municipality_hints": "; ".join(municipality_names),
        "geographic_name_hints": "; ".join(geographic_names),
    }


def enrich_records_with_location_hints(
    records: List[Dict[str, Any]],
    reference: pd.DataFrame,
) -> List[Dict[str, Any]]:
    enriched_records = []

    for record in records:
        enriched = dict(record)
        hints = find_location_hints_for_document(enriched, reference)
        flat = flatten_location_hints(hints)

        enriched["location_hints"] = hints
        enriched.update(flat)

        enriched_records.append(enriched)

    return enriched_records


def build_location_hinting_report(
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total_records = len(records)
    records_with_hints = sum(
        1 for record in records
        if int(record.get("location_hint_count", 0)) > 0
    )
    records_without_hints = total_records - records_with_hints
    total_hints = sum(
        int(record.get("location_hint_count", 0))
        for record in records
    )

    hint_type_counts: Dict[str, int] = {}

    for record in records:
        hints = record.get("location_hints", [])
        if not isinstance(hints, list):
            continue

        for hint in hints:
            hint_type = str(hint.get("hint_type", "unknown"))
            hint_type_counts[hint_type] = hint_type_counts.get(hint_type, 0) + 1

    return {
        "total_records": total_records,
        "records_with_hints": records_with_hints,
        "records_without_hints": records_without_hints,
        "total_hints": total_hints,
        "hint_type_counts": hint_type_counts,
    }


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_location_hinting(
    input_jsonl_path: Path,
    reference_path: Path,
    output_jsonl_path: Path,
    output_csv_path: Path,
    report_output_path: Path,
) -> Dict[str, Any]:
    records = load_jsonl(input_jsonl_path)
    reference = load_location_reference(reference_path)

    enriched_records = enrich_records_with_location_hints(records, reference)
    report = build_location_hinting_report(enriched_records)

    write_jsonl(output_jsonl_path, enriched_records)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(enriched_records).to_csv(
        output_csv_path,
        index=False,
        encoding="utf-8",
    )

    write_json(report_output_path, report)

    return report