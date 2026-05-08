from __future__ import annotations

import argparse
import json
from pathlib import Path

from changescout.enrichment.lead_enrichment import run_geoadmin_lead_location_enrichment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add GeoAdmin location hints to location enriched ChangeScout leads."
    )
    parser.add_argument(
        "--input",
        default="artifacts/leads_with_locations.jsonl",
        help="Input local location enriched leads JSONL.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="artifacts/leads_with_geoadmin_locations.jsonl",
        help="Output GeoAdmin enriched leads JSONL.",
    )
    parser.add_argument(
        "--output-csv",
        default="artifacts/leads_with_geoadmin_locations.csv",
        help="Output GeoAdmin enriched leads CSV.",
    )
    parser.add_argument(
        "--report-output",
        default="artifacts/geoadmin_location_hinting_report.json",
        help="Output GeoAdmin report JSON.",
    )
    parser.add_argument(
        "--cache",
        default="data/reference/geoadmin_search_cache.jsonl",
        help="GeoAdmin search cache JSONL.",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=3,
        help="Maximum GeoAdmin queries per lead.",
    )

    args = parser.parse_args()

    report = run_geoadmin_lead_location_enrichment(
        input_jsonl_path=Path(args.input),
        output_jsonl_path=Path(args.output_jsonl),
        output_csv_path=Path(args.output_csv),
        report_output_path=Path(args.report_output),
        cache_path=Path(args.cache),
        max_queries=args.max_queries,
    )

    print("GeoAdmin location enrichment completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote enriched leads JSONL: {args.output_jsonl}")
    print(f"Wrote enriched leads CSV: {args.output_csv}")
    print(f"Wrote report: {args.report_output}")
    print(f"Used cache: {args.cache}")


if __name__ == "__main__":
    main()
