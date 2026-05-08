#!/usr/bin/env bash

set -euo pipefail

RUN_ID="${RUN_ID:-annotation_expansion_discovery_test_001}"
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

for REGISTRY in "${REGISTRIES[@]}"; do
  echo ""
  echo "Testing discovery for registry: ${REGISTRY}"

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

  python - <<PY
import json
from collections import Counter
from pathlib import Path

path = Path("${REGISTRY_OUTPUT_DIR}/discovery.jsonl")
records = []

if path.exists():
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

print("records", len(records))
print("by_source", Counter(r.get("source_id") for r in records))

for record in records[:50]:
    print(record.get("source_id"), record.get("url"))
PY

done