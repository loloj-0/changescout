#!/usr/bin/env bash
set -euo pipefail

echo "ChangeScout baseline reproduction run"
echo "====================================="

echo
echo "Step 1: Check required inputs"

required_files=(
  "artifacts/discovery_ag.jsonl"
  "artifacts/discovery_sg_sample_final.jsonl"
  "artifacts/scored.jsonl"
  "artifacts/scored_be_unique_final.jsonl"
  "config/filter.yaml"
  "config/scoring.yaml"
  "data/annotation/labeled/annotation_full_reviewed.csv"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required file: $file"
    exit 1
  fi
done

echo "All required inputs found"

echo
echo "Step 2: Re crawl AG and SG with current decoding logic"

PYTHONPATH=src python -m changescout.cli crawl \
  --input artifacts/discovery_ag.jsonl \
  --output artifacts/crawl_ag_rerun.jsonl \
  --html-base-dir data/crawling \
  --run-id ag_run_002

PYTHONPATH=src python -m changescout.cli crawl \
  --input artifacts/discovery_sg_sample_final.jsonl \
  --output artifacts/crawl_sg_rerun.jsonl \
  --html-base-dir data/crawling \
  --run-id sg_run_002

echo
echo "Step 3: Clean AG and SG HTML"

PYTHONPATH=src python - <<'PY'
from changescout.html_cleaning import process_crawl_records

jobs = [
    {
        "input": "artifacts/crawl_ag_rerun.jsonl",
        "cleaned": "artifacts/cleaned_ag_rerun.jsonl",
        "excluded": "artifacts/excluded_ag_rerun.jsonl",
        "report": "artifacts/html_cleaning_report_ag_rerun.json",
    },
    {
        "input": "artifacts/crawl_sg_rerun.jsonl",
        "cleaned": "artifacts/cleaned_sg_rerun.jsonl",
        "excluded": "artifacts/excluded_sg_rerun.jsonl",
        "report": "artifacts/html_cleaning_report_sg_rerun.json",
    },
]

for job in jobs:
    report = process_crawl_records(
        input_path=job["input"],
        cleaned_output_path=job["cleaned"],
        excluded_output_path=job["excluded"],
        report_output_path=job["report"],
        min_text_length=300,
        allowed_languages=["de"],
    )
    print(job["cleaned"], report)
PY

echo
echo "Step 4: Filter AG and SG"

PYTHONPATH=src python -m changescout.cli filter \
  --input artifacts/cleaned_ag_rerun.jsonl \
  --config config/filter.yaml \
  --output artifacts/filtered_ag_rerun.jsonl \
  --excluded-output artifacts/filtered_excluded_ag_rerun.jsonl \
  --report-output artifacts/filter_report_ag_rerun.json

PYTHONPATH=src python -m changescout.cli filter \
  --input artifacts/cleaned_sg_rerun.jsonl \
  --config config/filter.yaml \
  --output artifacts/filtered_sg_rerun.jsonl \
  --excluded-output artifacts/filtered_excluded_sg_rerun.jsonl \
  --report-output artifacts/filter_report_sg_rerun.json

echo
echo "Step 5: Score AG and SG"

PYTHONPATH=src python -m changescout.cli score \
  --input artifacts/filtered_ag_rerun.jsonl \
  --config config/scoring.yaml \
  --output artifacts/scored_ag_rerun.jsonl \
  --report-output artifacts/scoring_report_ag_rerun.json

PYTHONPATH=src python -m changescout.cli score \
  --input artifacts/filtered_sg_rerun.jsonl \
  --config config/scoring.yaml \
  --output artifacts/scored_sg_rerun.jsonl \
  --report-output artifacts/scoring_report_sg_rerun.json

echo
echo "Step 6: Build scored annotation pool"

python - <<'PY'
from pathlib import Path
import json

input_paths = [
    Path("artifacts/scored.jsonl"),
    Path("artifacts/scored_ag_rerun.jsonl"),
    Path("artifacts/scored_be_unique_final.jsonl"),
    Path("artifacts/scored_sg_rerun.jsonl"),
]

output_path = Path("artifacts/scored_annotation_pool.jsonl")

seen = set()
written = 0

with output_path.open("w", encoding="utf-8") as out:
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(path)

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                record = json.loads(line)
                url = str(record.get("url", "")).strip()

                if not url or url in seen:
                    continue

                seen.add(url)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1

print(f"Wrote {written} records to {output_path}")

if written != 165:
    raise ValueError(f"Expected 165 records after hard filtering, got {written}")
PY

echo
echo "Step 7: Check text encoding quality"

python - <<'PY'
from pathlib import Path

path = Path("artifacts/scored_annotation_pool.jsonl")
text = path.read_text(encoding="utf-8", errors="replace")

markers = ["Ã", "Â", "�"]
failed = False

for marker in markers:
    count = text.count(marker)
    print(repr(marker), count)
    if count:
        failed = True

if failed:
    raise ValueError("Encoding quality check failed")
PY

echo
echo "Step 8: Run scoring evaluation"

PYTHONPATH=src python scripts/evaluate_scoring_against_annotations.py

echo
echo "Step 9: Run baseline classifier"

PYTHONPATH=src python scripts/train_baseline_classifier.py

echo
echo "Step 10: Generate baseline leads"

PYTHONPATH=src python scripts/generate_baseline_leads.py

echo
echo "Step 11: Print lead summary"

python - <<'PY'
import json
import pandas as pd
from pathlib import Path

report_path = Path("artifacts/lead_generation_report.json")
with report_path.open("r", encoding="utf-8") as f:
    report = json.load(f)

print(json.dumps(report, ensure_ascii=False, indent=2))

leads = pd.read_csv("artifacts/leads.csv")
print()
print("Top 10 leads")
print(leads.head(10)[["title", "source_id", "thematic_score", "lead_reason"]].to_string(index=False, max_colwidth=120))
PY

echo
echo "Baseline reproduction run completed"