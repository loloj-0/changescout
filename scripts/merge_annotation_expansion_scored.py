from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path} at line {line_number}") from error

            if not isinstance(record, dict):
                raise ValueError(f"Expected object in {path} at line {line_number}")

            records.append(record)

    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduplicated: list[dict[str, Any]] = []

    for record in records:
        source_id = str(record.get("source_id", "")).strip()
        url = str(record.get("url", "")).strip()

        key = (source_id, url)

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(record)

    return deduplicated


def collect_scored_files(input_root: Path) -> list[Path]:
    scored_files = sorted(input_root.glob("*/scored.jsonl"))
    return [path for path in scored_files if path.is_file()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge scored annotation expansion files into one JSONL file."
    )
    parser.add_argument(
        "--input-root",
        required=True,
        help="Root directory containing one subdirectory per registry.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Merged JSONL output path.",
    )
    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_path = Path(args.output)

    scored_files = collect_scored_files(input_root)

    if not scored_files:
        raise FileNotFoundError(f"No scored.jsonl files found under {input_root}")

    records: list[dict[str, Any]] = []

    for path in scored_files:
        loaded = load_jsonl(path)
        registry = path.parent.name

        for record in loaded:
            record.setdefault("annotation_expansion_registry", registry)

        records.extend(loaded)

    deduplicated = deduplicate_records(records)
    write_jsonl(output_path, deduplicated)

    print(f"scored_files: {len(scored_files)}")
    print(f"records_before_deduplication: {len(records)}")
    print(f"records_after_deduplication: {len(deduplicated)}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()