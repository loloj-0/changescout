#!/usr/bin/env bash

set -euo pipefail

RUN_ID="${RUN_ID:-annotation_expansion_001}"
REGISTRIES=("$@")

if [ "${#REGISTRIES[@]}" -eq 0 ]; then
  REGISTRIES=("gr" "lu" "so")
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BASE_OUTPUT_DIR="artifacts/annotation_expansion/${RUN_ID}"
TMP_CONFIG_BASE="${BASE_OUTPUT_DIR}/tmp_config"

mkdir -p "$BASE_OUTPUT_DIR"
mkdir -p "$TMP_CONFIG_BASE"

echo "Run ID: ${RUN_ID}"
echo "Registries: ${REGISTRIES[*]}"
echo "Output: ${BASE_OUTPUT_DIR}"

for REGISTRY in "${REGISTRIES[@]}"; do
  echo ""
  echo "Running annotation expansion for registry: ${REGISTRY}"

  REGISTRY_OUTPUT_DIR="${BASE_OUTPUT_DIR}/${REGISTRY}"
  TMP_CONFIG_DIR="${TMP_CONFIG_BASE}/${REGISTRY}"

  mkdir -p "$REGISTRY_OUTPUT_DIR"
  rm -rf "$TMP_CONFIG_DIR"
  cp -R config "$TMP_CONFIG_DIR"

  PYTHONPATH=src python - <<PY
from pathlib import Path

path = Path("${TMP_CONFIG_DIR}") / "scope.yaml"
text = path.read_text(encoding="utf-8")
lines = text.splitlines()

updated = []
replaced = False

for line in lines:
    if line.strip().startswith("source_registry:"):
        updated.append("source_registry: ${REGISTRY}")
        replaced = True
    else:
        updated.append(line)

if not replaced:
    updated.append("source_registry: ${REGISTRY}")

path.write_text("\\n".join(updated) + "\\n", encoding="utf-8")
PY

  PYTHONPATH=src python -m changescout.cli discover \
    --config-dir "$TMP_CONFIG_DIR" \
    --output "${REGISTRY_OUTPUT_DIR}/discovery.jsonl"

  PYTHONPATH=src python -m changescout.cli crawl \
    --input "${REGISTRY_OUTPUT_DIR}/discovery.jsonl" \
    --output "${REGISTRY_OUTPUT_DIR}/crawl.jsonl" \
    --html-base-dir data/crawling \
    --run-id "${RUN_ID}_${REGISTRY}"

  PYTHONPATH=src python - <<PY
from changescout.ingestion.html_cleaning import process_crawl_records

report = process_crawl_records(
    input_path="${REGISTRY_OUTPUT_DIR}/crawl.jsonl",
    cleaned_output_path="${REGISTRY_OUTPUT_DIR}/cleaned.jsonl",
    excluded_output_path="${REGISTRY_OUTPUT_DIR}/excluded.jsonl",
    report_output_path="${REGISTRY_OUTPUT_DIR}/html_cleaning_report.json",
    min_text_length=300,
    allowed_languages=["de"],
)
print(report)
PY

  PYTHONPATH=src python -m changescout.cli filter \
    --input "${REGISTRY_OUTPUT_DIR}/cleaned.jsonl" \
    --config config/filter.yaml \
    --output "${REGISTRY_OUTPUT_DIR}/filtered.jsonl" \
    --excluded-output "${REGISTRY_OUTPUT_DIR}/filtered_excluded.jsonl" \
    --report-output "${REGISTRY_OUTPUT_DIR}/filter_report.json"

  PYTHONPATH=src python -m changescout.cli score \
    --input "${REGISTRY_OUTPUT_DIR}/filtered.jsonl" \
    --config config/scoring.yaml \
    --output "${REGISTRY_OUTPUT_DIR}/scored.jsonl" \
    --report-output "${REGISTRY_OUTPUT_DIR}/scoring_report.json"
done

PYTHONPATH=src python tools/annotation/merge_annotation_expansion_scored.py \
  --input-root "$BASE_OUTPUT_DIR" \
  --output "${BASE_OUTPUT_DIR}/scored_annotation_expansion_merged.jsonl"

echo ""
echo "Done."
echo "Merged scored output: ${BASE_OUTPUT_DIR}/scored_annotation_expansion_merged.jsonl"