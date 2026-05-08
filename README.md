# ChangeScout

ChangeScout is a deterministic lead prioritization and review support pipeline for potential TLM relevant changes from official canton level web sources.

ChangeScout is not an automatic TLM update system.

ChangeScout does not replace expert judgement.

A lead is not a confirmed TLM change.

A lead is a source that should be reviewed because it may describe a persistent TLM road or path geometry update.

The workflow remains Human in the Loop.

## Purpose

ChangeScout supports reviewers by reducing manual search and screening effort.

It monitors manually curated official canton level source registries, extracts relevant text, scores candidate documents, selects review leads, enriches them with review aids, and writes scoped outputs for manual inspection.

The operational use case is inference on one selected source registry.

Typical questions are:

* Which official sources should a reviewer inspect first?
* Which leads have strong TLM geometry signals?
* Which leads are likely actionable according to the evaluated score and TF IDF setup?
* Which locations or GeoAdmin hints may help manual review?

ChangeScout should not answer:

* Should TLM be updated now?
* Is this project already built?
* Is this location a verified project geometry?

For the detailed project goal and evaluation framing, see:

`docs/project_goal.md`

For adding a new canton or source registry and running inference, see:

`docs/inference_runbook.md`

## Current operational capability

The current scoped operational workflow supports:

1. source registry validation and discovery smoke tests
2. source registry resolution
3. discovery
4. crawling
5. HTML cleaning
6. hard filtering
7. thematic scoring
8. optional operational TF IDF inference
9. candidate selection with `score_only` or `score_or_tfidf`
10. local location hinting on selected leads
11. optional GeoAdmin enrichment on selected leads
12. scoped review export package
13. scoped monitoring summary
14. run metadata and logs

Operational outputs are written under:

`artifacts/runs/<run_id>/`

Operational runs do not write to:

`data/annotation/evaluation/`

or:

`results/evaluation/`

The historical MVP reproduction workflow remains separate:

`bash scripts/operational/run.sh`

Do not mix the scoped operational inference workflow with the frozen evaluation and reproduction workflow.

## Repository structure

```text
src/changescout/
  ingestion/      discovery, crawling, cleaning, filtering
  ranking/        scoring, candidate selection, decision logic
  enrichment/     geography, local hints, GeoAdmin enrichment
  ml/             TF IDF, classification, LLM explainability
  review/         leads, review export, inference QA
  annotation/     annotation helpers
  validation/     registry validation and snapshots

scripts/
  operational/    scoped run helpers and review exports
  annotation/     annotation dataset construction and expansion
  evaluation/     evaluation and result package builders
  ml/             model training and LLM experiment scripts
  legacy/         historical MVP reproduction helpers

data/
  annotation/labeled/      curated labeled datasets
  annotation/evaluation/  frozen evaluation datasets
  models/                 tracked operational model artifacts
  reference/              stable reference files

results/
  evaluation/     generated evaluation results and report package

artifacts/
  generated operational run outputs, ignored by Git
```

## Environment setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Optional local LLM dependencies are separate because CUDA wheels are platform dependent.

```bash
source .venv/bin/activate
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r requirements-llm.txt
```

## Configuration

Monitoring is controlled by configuration.

### Scope config

`config/scope.yaml` defines:

* `version`
* `canton_id`
* `languages`
* `time_window_days`
* `source_registry`
* `source_policy`

### Source registry

`config/sources/<registry>.yaml` defines source entries.

Required fields for each source:

* `source_id`
* `name`
* `base_url`
* `crawl_type`
* `crawl_frequency_hours`
* `active`

For `crawl_type: html_pattern`, the source also requires:

* `include_patterns`

Example mapping:

`source_registry: "zh"` maps to `config/sources/zh.yaml`

For detailed instructions, see:

`docs/inference_runbook.md`

## Validate source registry

Before running a new source registry, validate its configuration.

```bash
PYTHONPATH=src python -m changescout.cli validate-registry \
  --config-dir config \
  --source-registry be
```

With discovery smoke test and scoped validation outputs:

```bash
PYTHONPATH=src python -m changescout.cli validate-registry \
  --config-dir config \
  --source-registry be \
  --smoke-discovery \
  --output-dir artifacts/registry_validation/be_001 \
  --timeout-seconds 10
```

This writes:

```text
artifacts/registry_validation/<run_id>/
  registry_validation_report.json
  discovery_smoke.jsonl
  discovery_smoke_report.json
```

The validation command checks required fields, duplicate `source_id`, active sources, supported `crawl_type`, required `include_patterns`, valid URLs, and broad include patterns.

## Resolve configured sources

```bash
PYTHONPATH=src python -m changescout.cli snapshot \
  --config-dir config \
  --snapshot-dir artifacts
```

This writes a resolved scope snapshot with the active sources.

## Standard inference preset

For regular inference, use the concise preset command.

The preset runs the recommended high recall setup:

* scoped operational run
* `score_or_tfidf` candidate selection
* default TF IDF artifact at `data/models/tfidf_actionable/tfidf_actionable_v1`
* local location hinting
* optional GeoAdmin enrichment

Minimal example:

```bash
PYTHONPATH=src python -m changescout.cli infer \
  --source-registry be \
  --canton-id be \
  --run-id be_infer_001
```

With optional GeoAdmin enrichment:

```bash
PYTHONPATH=src python -m changescout.cli infer \
  --source-registry be \
  --canton-id be \
  --run-id be_infer_geoadmin_001 \
  --enable-geoadmin-enrichment
```

The preset still writes only to:

`artifacts/runs/<run_id>/`

Use the full `run` command when custom thresholds, custom filter config, custom scoring config, or debugging options are needed.

## Run scoped operational inference

### Score only mode

This is the deterministic baseline mode.

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry zh \
  --canton-id zh \
  --run-id zh_score_only_001 \
  --output-root artifacts/runs \
  --html-root data/crawling \
  --lead-threshold 0.10 \
  --candidate-selection-mode score_only \
  --timeout-seconds 10
```

### Recommended high recall mode

The recommended current inference mode is `score_or_tfidf`.

It uses the union of:

* `thematic_score >= lead_threshold`
* `tfidf_actionable_probability >= tfidf_threshold`

It requires an explicit operational TF IDF model artifact.

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry be \
  --canton-id be \
  --run-id be_hybrid_001 \
  --output-root artifacts/runs \
  --html-root data/crawling \
  --lead-threshold 0.10 \
  --tfidf-threshold 0.50 \
  --candidate-selection-mode score_or_tfidf \
  --tfidf-model-artifact data/models/tfidf_actionable/tfidf_actionable_v1 \
  --timeout-seconds 10
```

### With optional GeoAdmin enrichment

GeoAdmin enrichment runs only on selected leads.

GeoAdmin hints are review aids only.

They are not verified project geometries.

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry be \
  --canton-id be \
  --run-id be_hybrid_geoadmin_001 \
  --output-root artifacts/runs \
  --html-root data/crawling \
  --lead-threshold 0.10 \
  --tfidf-threshold 0.50 \
  --candidate-selection-mode score_or_tfidf \
  --tfidf-model-artifact data/models/tfidf_actionable/tfidf_actionable_v1 \
  --enable-geoadmin-enrichment \
  --timeout-seconds 10
```

## Build review export package

After a scoped run, build a reviewer facing export package.

```bash
PYTHONPATH=src python scripts/operational/build_review_export.py \
  --run-dir artifacts/runs/be_hybrid_geoadmin_001 \
  --top-n 30
```

This writes:

```text
artifacts/runs/<run_id>/review/
  review_leads.csv
  review_summary.md
  review_export_report.json
```

The review export reads the best available lead output in this order:

1. `leads_with_llm_explanations.jsonl`
2. `leads_with_geoadmin_locations.jsonl`
3. `leads_with_locations.jsonl`
4. `leads.jsonl`

The export deduplicates repeated leads by canonical URL and preserves duplicate source ids.

## Build scoped monitoring summary

```bash
PYTHONPATH=src python scripts/operational/build_monitoring_summary.py \
  --run-id be_hybrid_geoadmin_001
```

This writes:

```text
artifacts/runs/<run_id>/monitoring_summary.json
artifacts/runs/<run_id>/monitoring_summary.md
```

The monitoring summary reads scoped run metadata and scoped stage reports.

It is a lightweight run summary.

It is not production alerting.

## Scoped operational output layout

A typical scoped run writes:

```text
artifacts/runs/<run_id>/
  scope_snapshot.json
  discovery.jsonl
  crawl.jsonl
  cleaned.jsonl
  excluded.jsonl
  filtered.jsonl
  filtered_excluded.jsonl
  scored.jsonl
  scored_with_tfidf.jsonl
  leads.jsonl
  leads.csv
  leads_with_locations.jsonl
  leads_with_locations.csv
  leads_with_geoadmin_locations.jsonl
  leads_with_geoadmin_locations.csv
  monitoring_summary.json
  monitoring_summary.md
  review/
    review_leads.csv
    review_summary.md
    review_export_report.json
  reports/
    discovery_report.json
    crawl_report.json
    cleaning_report.json
    filter_report.json
    scoring_report.json
    tfidf_inference_report.json
    lead_generation_report.json
    location_hinting_report.json
    geoadmin_location_hinting_report.json
  metadata/
    run_metadata.json
  logs/
    run.log
```

Some files are optional and exist only when the corresponding stage is enabled.

## Train operational TF IDF model artifact

```bash
PYTHONPATH=src python scripts/ml/train_operational_tfidf.py \
  --dataset data/annotation/evaluation/triage_3class_dataset.csv \
  --output-dir data/models/tfidf_actionable/tfidf_actionable_v1 \
  --model-version tfidf_actionable_v1
```

The target is actionable binary:

* positive: `confirmed_relevant`, `needs_review`
* negative: `not_relevant`

The tracked operational artifact contains:

```text
data/models/tfidf_actionable/tfidf_actionable_v1/
  model.joblib
  metadata.json
```

`test_predictions.csv` may be generated during training for audit purposes, but it is ignored by Git by default.

Operational runs load the artifact explicitly.

They do not retrain inside the inference run.

See:

`docs/model_artifacts.md`

## Standalone TF IDF inference

```bash
PYTHONPATH=src python scripts/operational/run_tfidf_inference.py \
  --input artifacts/runs/<run_id>/scored.jsonl \
  --output artifacts/runs/<run_id>/scored_with_tfidf.jsonl \
  --report-output artifacts/runs/<run_id>/reports/tfidf_inference_report.json \
  --artifact-dir data/models/tfidf_actionable/tfidf_actionable_v1
```

This adds:

* `tfidf_model_version`
* `tfidf_actionable_probability`
* `tfidf_actionable_prediction`
* `tfidf_actionable_threshold`

TF IDF probability is a learned review signal.

It is not a confirmed TLM relevance decision.

## Discovery only

```bash
PYTHONPATH=src python -m changescout.cli discover \
  --config-dir config \
  --output artifacts/discovery.jsonl
```

Discovery:

* fetches source HTML
* extracts links
* normalizes URLs
* filters by include patterns
* removes binary assets
* deduplicates canonical URLs
* writes JSONL

## Crawling only

```bash
PYTHONPATH=src python -m changescout.cli crawl \
  --input artifacts/discovery.jsonl \
  --output artifacts/crawl.jsonl \
  --html-base-dir data/crawling \
  --run-id run_001
```

Crawling:

* fetches discovered URLs
* stores raw HTML
* computes content hash
* writes structured crawl records
* continues on errors

## HTML cleaning only

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry <registry> \
  --canton-id <canton> \
  --run-id <run_id>
```

HTML cleaning:

* reads raw HTML files
* extracts title and main content
* removes boilerplate
* normalizes text
* applies basic quality filtering
* writes cleaned and excluded outputs

## Hard filtering only

```bash
PYTHONPATH=src python -m changescout.cli filter \
  --input artifacts/cleaned.jsonl \
  --config config/filter.yaml \
  --output artifacts/filtered.jsonl \
  --excluded-output artifacts/filtered_excluded.jsonl \
  --report-output artifacts/filter_report.json
```

Hard filtering:

* removes clearly non domain documents
* preserves plausible infrastructure related content
* writes filtering signals and report

## Thematic scoring only

```bash
PYTHONPATH=src python -m changescout.cli score \
  --input artifacts/filtered.jsonl \
  --config config/scoring.yaml \
  --output artifacts/scored.jsonl \
  --report-output artifacts/scoring_report.json
```

Scoring:

* computes deterministic thematic relevance signals
* writes `thematic_score`
* writes inspectable scoring signals
* writes scoring report

## Standalone lead enrichment

### Local location hinting

```bash
PYTHONPATH=src python scripts/operational/add_location_hints_to_leads.py \
  --input artifacts/runs/<run_id>/leads.jsonl \
  --reference data/reference/location_hints_reference.csv \
  --output-jsonl artifacts/runs/<run_id>/leads_with_locations.jsonl \
  --output-csv artifacts/runs/<run_id>/leads_with_locations.csv \
  --report-output artifacts/runs/<run_id>/reports/location_hinting_report.json
```

### GeoAdmin enrichment

```bash
PYTHONPATH=src python scripts/operational/enrich_location_hints_geoadmin.py \
  --input artifacts/runs/<run_id>/leads_with_locations.jsonl \
  --output-jsonl artifacts/runs/<run_id>/leads_with_geoadmin_locations.jsonl \
  --output-csv artifacts/runs/<run_id>/leads_with_geoadmin_locations.csv \
  --report-output artifacts/runs/<run_id>/reports/geoadmin_location_hinting_report.json \
  --cache data/reference/geoadmin_search_cache.jsonl \
  --max-queries 3
```

GeoAdmin enrichment is optional and non authoritative.

API failure does not invalidate lead generation.

## Evaluation workflow

Frozen evaluation datasets are stored under:

`data/annotation/evaluation/`

Generated evaluation results are stored under:

`results/evaluation/`

The expanded annotation dataset contains 348 manually reviewed sources.

Generated evaluation datasets:

| Dataset | Rows | Train | Test | Positive class | Excluded class |
|---|---:|---:|---:|---|---|
| strict_binary | 264 | 211 | 53 | confirmed_relevant | needs_review |
| actionable_binary | 348 | 278 | 70 | confirmed_relevant or needs_review | none |
| triage_3class | 348 | 278 | 70 | three class target | none |

Build evaluation datasets:

```bash
PYTHONPATH=src python scripts/evaluation/build_evaluation_datasets.py
```

Evaluate deterministic score baseline:

```bash
PYTHONPATH=src python scripts/evaluation/evaluate_score_baseline.py
```

Evaluate classical TF IDF baseline:

```bash
PYTHONPATH=src python scripts/evaluation/evaluate_classical_text_classifier.py
```

Run local LLM triage evaluation:

```bash
PYTHONPATH=src python scripts/ml/run_local_llm_triage.py \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --prompt-variant hierarchical

PYTHONPATH=src python scripts/evaluation/evaluate_local_llm_triage.py \
  --predictions results/evaluation/local_llm/Qwen__Qwen2.5-7B-Instruct/hierarchical/llm_triage_predictions.jsonl
```

Evaluate aligned method comparison:

```bash
PYTHONPATH=src python scripts/evaluation/evaluate_aligned_method_comparison.py
```

Evaluate hybrid lead selection:

```bash
PYTHONPATH=src python scripts/evaluation/evaluate_hybrid_lead_selection.py \
  --llm-predictions results/evaluation/local_llm/Qwen__Qwen2.5-7B-Instruct/direct/llm_triage_predictions.jsonl \
  --output-dir results/evaluation/hybrid_lead_selection_qwen7b_direct

PYTHONPATH=src python scripts/evaluation/compare_hybrid_lead_selection_runs.py
```

Build report package:

```bash
PYTHONPATH=src python scripts/evaluation/build_evaluation_report_package.py
```

The report package is written to:

`results/evaluation/report_package/`

## Current method findings

Task specific binary split results:

| Dataset | Method | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| strict_binary | thematic_score | 0.864 | 0.760 | 0.809 |
| strict_binary | TF IDF Logistic Regression | 0.852 | 0.920 | 0.885 |
| actionable_binary | thematic_score | 0.771 | 0.881 | 0.822 |
| actionable_binary | TF IDF Logistic Regression | 0.812 | 0.929 | 0.867 |

Aligned triage test split results:

| Task | Method | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| strict_binary | thematic_score | 0.957 | 0.880 | 0.917 |
| actionable_binary | thematic_score | 0.750 | 0.857 | 0.800 |
| actionable_binary | TF IDF Logistic Regression | 0.771 | 0.881 | 0.822 |
| actionable_binary | Qwen2.5 14B hierarchical | 0.969 | 0.738 | 0.838 |

Hybrid lead selection findings:

| Review depth | Best mode | Precision at N | Recall at N | False negatives |
|---:|---|---:|---:|---:|
| 10 | `tfidf_only` | 1.000 | 0.238 | 32 |
| 20 | `hybrid_recall_guard` | 1.000 | 0.476 | 22 |
| 50 | `score_or_tfidf` | 0.780 | 0.929 | 3 |
| 70 | `score_or_tfidf` | 0.600 | 1.000 | 0 |

Recommended current setup:

1. use `score_or_tfidf` for high recall candidate selection
2. use local LLMs for explanation and review support, not hard exclusion
3. treat GeoAdmin hints as review aids only
4. keep the final decision with human reviewers

## Current limitations

ChangeScout currently does not:

* confirm whether a lead corresponds to a finished real world change
* update TLM automatically
* verify project geometries
* provide a production scheduler
* provide production alerting
* guarantee canton independent generalization
* provide a stable standalone LLM classifier

Additional limitations:

* HTML cleaning prioritizes recall over precision
* thematic scoring is transparent but keyword and pattern based
* TF IDF is a learned review signal and can be miscalibrated on new source types
* local LLMs are conservative and not stable enough as hard classifiers
* GeoAdmin results are heuristic and sometimes noisy
* review exports are aids for manual inspection, not final decisions

## Script inventory

The repository contains operational code, MVP reproduction helpers, annotation tools, and evaluation scripts.

Script responsibilities are documented in:

`docs/script_inventory.md`

Current standard inference entry point:

```bash
PYTHONPATH=src python -m changescout.cli infer
```

Full operational entry point:

```bash
PYTHONPATH=src python -m changescout.cli run
```

Historical MVP reproduction entry point:

```bash
bash scripts/operational/run.sh
```

## Tests

Run all tests:

```bash
PYTHONPATH=src pytest -q
```

## Generated data policy

Generated operational outputs belong under:

`artifacts/runs/<run_id>/`

Raw crawled HTML belongs under:

`data/crawling/<run_id>/`

GeoAdmin cache is local generated data:

`data/reference/geoadmin_search_cache.jsonl`

Frozen evaluation datasets belong under:

`data/annotation/evaluation/`

Generated evaluation results belong under:

`results/evaluation/`

Operational inference must not overwrite frozen evaluation datasets or curated evaluation results.

## Demo Runbook

For a compact reproducible demo run, see `docs/demo_runbook.md`.


## Labeled dataset

The canonical labeled dataset is `data/annotation/labeled/annotation_dataset_expanded.csv`. It contains 348 manually reviewed records from multiple cantons. `annotation_dataset_expanded.jsonl` is the equivalent machine readable copy.
