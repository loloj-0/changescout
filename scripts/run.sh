#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${RUN_ID:-$(date -u +"%Y%m%dT%H%M%SZ")}"
RUN_DIR="artifacts/runs/${RUN_ID}"
RUN_LOG_DIR="${RUN_DIR}/logs"
RUN_LOG_PATH="${RUN_LOG_DIR}/run.log"
RUN_METADATA_PATH="${RUN_DIR}/run_metadata.json"
ENABLE_GEOADMIN_VALUE="${ENABLE_GEOADMIN_ENRICHMENT:-0}"

mkdir -p "${RUN_LOG_DIR}"

exec > >(tee -a "${RUN_LOG_PATH}") 2>&1

write_run_metadata() {
  local status="$1"
  local failed_line="${2:-}"

  python - <<PY
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess

metadata_path = Path("${RUN_METADATA_PATH}")
metadata_path.parent.mkdir(parents=True, exist_ok=True)

now = datetime.now(timezone.utc).isoformat()

if metadata_path.exists():
    with metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
else:
    metadata = {
        "run_id": "${RUN_ID}",
        "started_at": now,
    }

try:
    git_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()
except Exception:
    git_commit = ""

try:
    git_status_short = subprocess.check_output(
        ["git", "status", "--short"],
        text=True,
    ).strip()
except Exception:
    git_status_short = ""

metadata.update(
    {
        "run_id": "${RUN_ID}",
        "status": "${status}",
        "started_at": metadata.get("started_at", now),
        "updated_at": now,
        "ended_at": now if "${status}" in {"success", "failed"} else "",
        "failed_line": "${failed_line}",
        "geo_admin_enrichment_enabled": "${ENABLE_GEOADMIN_VALUE}" == "1",
        "git_commit": git_commit,
        "git_status_short": git_status_short,
        "log_path": "${RUN_LOG_PATH}",
        "config_paths": {
            "filter_config": "config/filter.yaml",
            "scoring_config": "config/scoring.yaml",
            "annotation_dataset": "data/annotation/labeled/annotation_full_reviewed.csv",
        },
        "input_paths": {
            "discovery_ag": "artifacts/discovery_ag.jsonl",
            "discovery_sg": "artifacts/discovery_sg_sample_final.jsonl",
            "scored_zh_existing": "artifacts/scored.jsonl",
            "scored_be_existing": "artifacts/scored_be_unique_final.jsonl",
        },
        "report_paths": {
            "html_cleaning_ag": "artifacts/html_cleaning_report_ag_rerun.json",
            "html_cleaning_sg": "artifacts/html_cleaning_report_sg_rerun.json",
            "filter_ag": "artifacts/filter_report_ag_rerun.json",
            "filter_sg": "artifacts/filter_report_sg_rerun.json",
            "scoring_ag": "artifacts/scoring_report_ag_rerun.json",
            "scoring_sg": "artifacts/scoring_report_sg_rerun.json",
            "lead_generation": "artifacts/lead_generation_report.json",
            "local_location_hinting": "artifacts/location_hinting_report.json",
            "geoadmin_location_hinting": "artifacts/geoadmin_location_hinting_report.json",
            "monitoring_summary": "artifacts/monitoring_summary.json",
        },
        "output_paths": {
            "scored_annotation_pool": "artifacts/scored_annotation_pool.jsonl",
            "leads_jsonl": "artifacts/leads.jsonl",
            "leads_csv": "artifacts/leads.csv",
            "local_location_leads_jsonl": "artifacts/leads_with_locations.jsonl",
            "local_location_leads_csv": "artifacts/leads_with_locations.csv",
            "geoadmin_location_leads_jsonl": "artifacts/leads_with_geoadmin_locations.jsonl",
            "geoadmin_location_leads_csv": "artifacts/leads_with_geoadmin_locations.csv",
            "monitoring_summary_json": "artifacts/monitoring_summary.json",
            "monitoring_summary_markdown": "artifacts/monitoring_summary.md",
        },
    }
)

with metadata_path.open("w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

handle_failure() {
  local line_number="$1"
  write_run_metadata "failed" "${line_number}"
}

trap 'handle_failure "$LINENO"' ERR

write_run_metadata "running"

echo "ChangeScout baseline reproduction run"
echo "====================================="
echo "Run ID: ${RUN_ID}"
echo "Run directory: ${RUN_DIR}"
echo "Run log: ${RUN_LOG_PATH}"
echo "GeoAdmin enrichment enabled: ${ENABLE_GEOADMIN_VALUE}"

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
echo "Step 6: Build scored annotation pool from existing ZH and BE plus rerun AG and SG"

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
echo "Step 11: Add local location hints to baseline leads"

PYTHONPATH=src python scripts/add_location_hints_to_leads.py

echo
echo "Step 12: Optionally enrich location hints with GeoAdmin Search API"

if [[ "${ENABLE_GEOADMIN_ENRICHMENT:-0}" == "1" ]]; then
  PYTHONPATH=src python scripts/enrich_location_hints_geoadmin.py
else
  echo "Skipping GeoAdmin enrichment. Set ENABLE_GEOADMIN_ENRICHMENT=1 to enable."

  rm -f \
    artifacts/leads_with_geoadmin_locations.jsonl \
    artifacts/leads_with_geoadmin_locations.csv \
    artifacts/geoadmin_location_hinting_report.json
fi

echo
echo "Step 13: Print lead and location hint summary"

python - <<'PY'
import json
import pandas as pd
from pathlib import Path

lead_report_path = Path("artifacts/lead_generation_report.json")
with lead_report_path.open("r", encoding="utf-8") as f:
    lead_report = json.load(f)

print("Lead generation report")
print(json.dumps(lead_report, ensure_ascii=False, indent=2))

hint_report_path = Path("artifacts/location_hinting_report.json")
with hint_report_path.open("r", encoding="utf-8") as f:
    hint_report = json.load(f)

print()
print("Location hinting report")
print(json.dumps(hint_report, ensure_ascii=False, indent=2))

geoadmin_report_path = Path("artifacts/geoadmin_location_hinting_report.json")
geoadmin_output_path = Path("artifacts/leads_with_geoadmin_locations.csv")
local_output_path = Path("artifacts/leads_with_locations.csv")

if geoadmin_report_path.exists() and geoadmin_output_path.exists():
    with geoadmin_report_path.open("r", encoding="utf-8") as f:
        geoadmin_report = json.load(f)

    print()
    print("GeoAdmin location hinting report")
    print(json.dumps(geoadmin_report, ensure_ascii=False, indent=2))

    leads = pd.read_csv(geoadmin_output_path)
    columns = [
        "title",
        "source_id",
        "thematic_score",
        "lead_reason",
        "location_hint_count",
        "geoadmin_preferred_canton",
        "geoadmin_location_hint_count",
        "geoadmin_top_location_name",
        "geoadmin_best_location_x",
        "geoadmin_best_location_y",
    ]

    print()
    print("Top 10 leads with GeoAdmin location hints")
else:
    leads = pd.read_csv(local_output_path)
    columns = [
        "title",
        "source_id",
        "thematic_score",
        "lead_reason",
        "location_hint_count",
    ]

    print()
    print("Top 10 leads with local location hints")

print(leads.head(10)[columns].to_string(index=False, max_colwidth=120))
PY

echo
echo "Step 14: Build monitoring summary"

write_run_metadata "success"
PYTHONPATH=src python scripts/build_monitoring_summary.py
write_run_metadata "success"

echo
echo "Baseline reproduction run completed"
echo "Run metadata written to ${RUN_METADATA_PATH}"
echo "Run log written to ${RUN_LOG_PATH}"
echo "Monitoring summary written to artifacts/monitoring_summary.json"
echo "Monitoring summary Markdown written to artifacts/monitoring_summary.md"