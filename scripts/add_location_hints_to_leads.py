from __future__ import annotations

from pathlib import Path
import json

from changescout.geography import run_location_hinting


INPUT_JSONL_PATH = Path("artifacts/leads.jsonl")
REFERENCE_PATH = Path("data/reference/location_hints_reference.csv")
OUTPUT_JSONL_PATH = Path("artifacts/leads_with_locations.jsonl")
OUTPUT_CSV_PATH = Path("artifacts/leads_with_locations.csv")
REPORT_OUTPUT_PATH = Path("artifacts/location_hinting_report.json")


def main() -> None:
    report = run_location_hinting(
        input_jsonl_path=INPUT_JSONL_PATH,
        reference_path=REFERENCE_PATH,
        output_jsonl_path=OUTPUT_JSONL_PATH,
        output_csv_path=OUTPUT_CSV_PATH,
        report_output_path=REPORT_OUTPUT_PATH,
    )

    print("Location hinting completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote enriched leads JSONL: {OUTPUT_JSONL_PATH}")
    print(f"Wrote enriched leads CSV: {OUTPUT_CSV_PATH}")
    print(f"Wrote report: {REPORT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()