from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

import pandas as pd

from changescout.geoadmin import enrich_lead_with_geoadmin_hints


INPUT_JSONL_PATH = Path("artifacts/leads_with_locations.jsonl")
OUTPUT_JSONL_PATH = Path("artifacts/leads_with_geoadmin_locations.jsonl")
OUTPUT_CSV_PATH = Path("artifacts/leads_with_geoadmin_locations.csv")
REPORT_OUTPUT_PATH = Path("artifacts/geoadmin_location_hinting_report.json")
CACHE_PATH = Path("data/reference/geoadmin_search_cache.jsonl")


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


def flatten_geoadmin_hints(record: Dict[str, Any]) -> Dict[str, Any]:
    hints = record.get("geoadmin_location_hints", [])

    if not isinstance(hints, list):
        hints = []

    names = []
    origins = []
    queries = []

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


def build_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
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


def run_geoadmin_enrichment() -> Dict[str, Any]:
    records = load_jsonl(INPUT_JSONL_PATH)

    enriched_records = []

    for record in records:
        enriched = enrich_lead_with_geoadmin_hints(
            lead=record,
            cache_path=CACHE_PATH,
            max_queries=3,
        )

        enriched.update(flatten_geoadmin_hints(enriched))
        enriched_records.append(enriched)

    report = build_report(enriched_records)

    write_jsonl(OUTPUT_JSONL_PATH, enriched_records)

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(enriched_records).to_csv(
        OUTPUT_CSV_PATH,
        index=False,
        encoding="utf-8",
    )

    write_json(REPORT_OUTPUT_PATH, report)

    return report


def main() -> None:
    report = run_geoadmin_enrichment()

    print("GeoAdmin location enrichment completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote enriched leads JSONL: {OUTPUT_JSONL_PATH}")
    print(f"Wrote enriched leads CSV: {OUTPUT_CSV_PATH}")
    print(f"Wrote report: {REPORT_OUTPUT_PATH}")
    print(f"Used cache: {CACHE_PATH}")


if __name__ == "__main__":
    main()