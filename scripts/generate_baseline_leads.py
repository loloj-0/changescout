from __future__ import annotations

from pathlib import Path
import json

from changescout.leads import run_lead_generation


SCORED_PATH = Path("artifacts/scored_annotation_pool.jsonl")
CLASSIFIER_PREDICTIONS_PATH = Path(
    "data/annotation/evaluation/baseline_classifier_predictions.csv"
)

OUTPUT_JSONL_PATH = Path("artifacts/leads.jsonl")
OUTPUT_CSV_PATH = Path("artifacts/leads.csv")
REPORT_OUTPUT_PATH = Path("artifacts/lead_generation_report.json")

LEAD_THRESHOLD = 0.10
PREVIEW_LENGTH = 500


def main() -> None:
    classifier_predictions_path = (
        CLASSIFIER_PREDICTIONS_PATH
        if CLASSIFIER_PREDICTIONS_PATH.exists()
        else None
    )

    report = run_lead_generation(
        scored_path=SCORED_PATH,
        classifier_predictions_path=classifier_predictions_path,
        output_jsonl_path=OUTPUT_JSONL_PATH,
        output_csv_path=OUTPUT_CSV_PATH,
        report_output_path=REPORT_OUTPUT_PATH,
        threshold=LEAD_THRESHOLD,
        preview_length=PREVIEW_LENGTH,
    )

    print("Baseline lead generation completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote leads JSONL: {OUTPUT_JSONL_PATH}")
    print(f"Wrote leads CSV: {OUTPUT_CSV_PATH}")
    print(f"Wrote report: {REPORT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()