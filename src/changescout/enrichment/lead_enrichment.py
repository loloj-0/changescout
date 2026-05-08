from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

import pandas as pd

from changescout.enrichment.geoadmin import enrich_lead_with_geoadmin_hints
from changescout.enrichment.geography import run_location_hinting


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def run_local_lead_location_hinting(
    input_jsonl_path: Path,
    reference_path: Path,
    output_jsonl_path: Path,
    output_csv_path: Path,
    report_output_path: Path,
) -> Dict[str, Any]:
    return run_location_hinting(
        input_jsonl_path=input_jsonl_path,
        reference_path=reference_path,
        output_jsonl_path=output_jsonl_path,
        output_csv_path=output_csv_path,
        report_output_path=report_output_path,
    )


def flatten_geoadmin_hints(record: Dict[str, Any]) -> Dict[str, Any]:
    hints = record.get("geoadmin_location_hints", [])

    if not isinstance(hints, list):
        hints = []

    names: list[str] = []
    origins: list[str] = []
    queries: list[str] = []

    for hint in hints:
        if not isinstance(hint, dict):
            continue

        name = str(hint.get("name", "")).strip()
        origin = str(hint.get("origin", "")).strip()
        query = str(hint.get("query", "")).strip()

        if name:
            names.append(name)
        if origin:
            origins.append(origin)
        if query:
            queries.append(query)

    return {
        "geoadmin_location_hint_names": "; ".join(names),
        "geoadmin_location_origins": "; ".join(sorted(set(origins))),
        "geoadmin_location_queries": "; ".join(sorted(set(queries))),
        "geoadmin_top_location_name": names[0] if names else "",
    }


def build_geoadmin_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_records = len(records)

    records_with_hints = sum(
        1
        for record in records
        if int(record.get("geoadmin_location_hint_count", 0)) > 0
    )

    records_without_hints = total_records - records_with_hints

    total_hints = sum(
        int(record.get("geoadmin_location_hint_count", 0))
        for record in records
    )

    total_queries = sum(
        int(record.get("geoadmin_query_count", 0))
        for record in records
    )

    total_cache_hits = sum(
        int(record.get("geoadmin_cache_hits", 0))
        for record in records
    )

    total_cache_misses = sum(
        int(record.get("geoadmin_cache_misses", 0))
        for record in records
    )

    origin_counts: Dict[str, int] = {}

    for record in records:
        hints = record.get("geoadmin_location_hints", [])

        if not isinstance(hints, list):
            continue

        for hint in hints:
            if not isinstance(hint, dict):
                continue

            origin = str(hint.get("origin", "unknown"))
            origin_counts[origin] = origin_counts.get(origin, 0) + 1

    return {
        "total_records": total_records,
        "records_with_geoadmin_hints": records_with_hints,
        "records_without_geoadmin_hints": records_without_hints,
        "total_geoadmin_hints": total_hints,
        "total_geoadmin_queries": total_queries,
        "total_cache_hits": total_cache_hits,
        "total_cache_misses": total_cache_misses,
        "origin_counts": origin_counts,
    }


def run_geoadmin_lead_location_enrichment(
    input_jsonl_path: Path,
    output_jsonl_path: Path,
    output_csv_path: Path,
    report_output_path: Path,
    cache_path: Path,
    max_queries: int = 3,
) -> Dict[str, Any]:
    records = load_jsonl(input_jsonl_path)
    enriched_records: List[Dict[str, Any]] = []

    for record in records:
        enriched = enrich_lead_with_geoadmin_hints(
            lead=record,
            cache_path=cache_path,
            max_queries=max_queries,
        )

        enriched.update(flatten_geoadmin_hints(enriched))
        enriched_records.append(enriched)

    report = build_geoadmin_report(enriched_records)

    write_jsonl(output_jsonl_path, enriched_records)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(enriched_records).to_csv(
        output_csv_path,
        index=False,
        encoding="utf-8",
    )

    write_json(report_output_path, report)

    return report


def write_geoadmin_failure_report(
    report_output_path: Path,
    error: str,
) -> Dict[str, Any]:
    report = {
        "status": "failed_non_blocking",
        "error": error,
        "total_records": 0,
        "records_with_geoadmin_hints": 0,
        "records_without_geoadmin_hints": 0,
        "total_geoadmin_hints": 0,
        "total_geoadmin_queries": 0,
        "total_cache_hits": 0,
        "total_cache_misses": 0,
        "origin_counts": {},
    }

    write_json(report_output_path, report)

    return report
