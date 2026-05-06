from __future__ import annotations

import argparse
import json
from pathlib import Path

from changescout.lead_enrichment import run_local_lead_location_hinting


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add local location hints to ChangeScout leads."
    )
    parser.add_argument(
        "--input",
        default="artifacts/leads.jsonl",
        help="Input leads JSONL.",
    )
    parser.add_argument(
        "--reference",
        default="data/reference/location_hints_reference.csv",
        help="Location hint reference CSV.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="artifacts/leads_with_locations.jsonl",
        help="Output enriched leads JSONL.",
    )
    parser.add_argument(
        "--output-csv",
        default="artifacts/leads_with_locations.csv",
        help="Output enriched leads CSV.",
    )
    parser.add_argument(
        "--report-output",
        default="artifacts/location_hinting_report.json",
        help="Output report JSON.",
    )

    args = parser.parse_args()

    report = run_local_lead_location_hinting(
        input_jsonl_path=Path(args.input),
        reference_path=Path(args.reference),
        output_jsonl_path=Path(args.output_jsonl),
        output_csv_path=Path(args.output_csv),
        report_output_path=Path(args.report_output),
    )

    print("Location hinting completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote enriched leads JSONL: {args.output_jsonl}")
    print(f"Wrote enriched leads CSV: {args.output_csv}")
    print(f"Wrote report: {args.report_output}")


if __name__ == "__main__":
    main()
