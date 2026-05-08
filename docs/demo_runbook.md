# ChangeScout Demo Runbook

## Zweck

Dieses Runbook beschreibt einen kompakten End to End Demo Run mit einer kuratierten, nicht im Training verwendeten Quelle.

Die Demo Quelle ist `fr_demo`.

Sie nutzt deutschsprachige Seiten des Kantons Freiburg zu Strassenprojekten und verwandten Infrastrukturseiten.

## Voraussetzung

Repository ist installiert und Tests laufen.

```bash
.venv/bin/python -m pytest
```

## Demo Registry prüfen

```bash
REGISTRY=fr_demo
CANTON=fr
RUN_ID=fr_demo_curated_001

.venv/bin/python -m changescout.cli validate-registry \
  --config-dir config \
  --source-registry "$REGISTRY" \
  --smoke-discovery \
  --output-dir "artifacts/registry_validation/${RUN_ID}_smoke" \
  --timeout-seconds 10
```

Erwartung:

```text
valid=True
smoke_status=success
smoke_records=5
```

## Operational Inference Run

```bash
.venv/bin/python -m changescout.cli infer \
  --source-registry "$REGISTRY" \
  --canton-id "$CANTON" \
  --run-id "$RUN_ID" \
  --enable-geoadmin-enrichment
```

Dieser Schritt führt Discovery, Crawling, Cleaning, Filtering, Scoring, TF IDF Inference, Lead Selection, lokales Location Hinting und GeoAdmin Enrichment aus.

## LLM Explainability

```bash
.venv/bin/python scripts/ml/run_scoped_llm_explainability.py \
  --run-dir "artifacts/runs/$RUN_ID" \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --max-new-tokens 384
```

Der LLM Schritt erklärt nur bereits ausgewählte Leads. Er selektiert keine Leads und entfernt keine Leads.

## Review Export

```bash
.venv/bin/python scripts/operational/build_review_export.py \
  --run-dir "artifacts/runs/$RUN_ID" \
  --top-n 30
```

Wichtige Outputs:

```text
artifacts/runs/fr_demo_curated_001/review/review_summary.md
artifacts/runs/fr_demo_curated_001/review/review_leads.csv
```

## QA und Monitoring

```bash
.venv/bin/python scripts/operational/build_inference_qa_report.py \
  --run-dir "artifacts/runs/$RUN_ID"

.venv/bin/python scripts/operational/build_monitoring_summary.py \
  --run-id "$RUN_ID"
```

Wichtige Outputs:

```text
artifacts/runs/fr_demo_curated_001/reports/inference_qa_report.md
artifacts/runs/fr_demo_curated_001/monitoring_summary.md
```

## Resultate anzeigen

```bash
cat "artifacts/runs/$RUN_ID/review/review_summary.md"
cat "artifacts/runs/$RUN_ID/reports/inference_qa_report.md"
cat "artifacts/runs/$RUN_ID/monitoring_summary.md"
```

## Erwartetes Demo Verhalten

Der Run sollte 5 Seiten entdecken und 4 Leads exportieren.

Der wichtigste positive Demo Lead ist:

```text
Neue Strassenverbindung Marly-Matran
```

Der LLM sollte diesen Lead als `confirmed_geometry` einordnen.

Weitere Leads zeigen, dass ChangeScout auch Review Fälle und schwächere Hinweise sichtbar macht.

## Git Hygiene

Run Artefakte werden nicht versioniert.

```bash
git status --short
git status --short --ignored artifacts data/crawling data/reference | head -100
```

Erwartung:

```text
config/sources/fr_demo.yaml
```

ist versioniert oder staged.

`artifacts/`, `data/crawling/` und GeoAdmin Cache bleiben ignoriert.
