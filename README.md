# ChangeScout

ChangeScout is a deterministic monitoring pipeline for canton scoped observation of official web sources.

## Project goal

ChangeScout is a deterministic lead prioritization and review support pipeline for potential TLM relevant changes.

The system monitors manually curated official canton level web sources, processes source text, ranks candidate documents, and produces reviewable leads.

ChangeScout is not an automatic TLM update system.

ChangeScout does not replace expert judgement.

The goal is to reduce manual search and screening effort by surfacing potentially relevant official sources earlier and in a reproducible priority order.

A lead is not a confirmed TLM change.

A lead is a source that should be reviewed because it may describe a persistent TLM road or path geometry update.

The main workflow remains human in the loop.

For the detailed project goal and evaluation framing, see:

`docs/project_goal.md`

## Current MVP source model

The MVP supports manually curated official source definitions in a versioned registry.

A source can currently be defined as:

* `html_list` for a concrete list page
* `html_pattern` for a section root plus URL include patterns used to discover relevant subpages

This allows the MVP to monitor official infrastructure project sections even when no clean central list page is available.

## Configuration

Monitoring is controlled entirely via configuration.

### Scope

`config/scope.yaml` defines:

* `version`
* `canton_id`
* `languages`
* `time_window_days`
* `source_registry`
* `source_policy`

### Source registry

`config/sources/<registry>.yaml` defines:

* `source_id`
* `name`
* `base_url`
* `crawl_type`
* `include_patterns` for `html_pattern`
* `crawl_frequency_hours`
* `active`

The value of `source_registry` in `config/scope.yaml` maps directly to the registry file name.

Example:

* `source_registry: "zh"` maps to `config/sources/zh.yaml`

Only sources defined in that file are used by the pipeline.

## Usage

### Environment setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Optional local LLM environment setup

Local LLM evaluation requires additional dependencies.

```bash
source .venv/bin/activate
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r requirements-llm.txt
```

Torch is intentionally not part of the base `requirements.txt` because CUDA wheels are platform dependent.

### Resolve configured sources and generate a snapshot

```bash
PYTHONPATH=src python -m changescout.cli snapshot --config-dir config --snapshot-dir artifacts
```

### Run discovery

```bash
PYTHONPATH=src python -m changescout.cli discover --config-dir config --output artifacts/discovery.jsonl
```

### Run crawling

```bash
PYTHONPATH=src python -m changescout.cli crawl \
  --input artifacts/discovery.jsonl \
  --output artifacts/crawl.jsonl \
  --html-base-dir data/crawling \
  --run-id run_001
```

### Run HTML cleaning

```bash
PYTHONPATH=src python -m changescout.html_cleaning
```

This step:

* loads crawl output
* reads raw HTML files
* extracts title and main content using source specific rules
* removes boilerplate sections
* normalizes text
* applies technical quality filtering
* writes cleaned documents
* writes excluded documents
* generates a cleaning report

### Run hard filtering

```bash
PYTHONPATH=src python -m changescout.cli filter \
  --input artifacts/cleaned.jsonl \
  --config config/filter.yaml \
  --output artifacts/filtered.jsonl \
  --excluded-output artifacts/filtered_excluded.jsonl \
  --report-output artifacts/filter_report.json
```

This step:

* removes clearly non domain documents
* preserves all plausible infrastructure related content
* enriches documents with simple rule based signals
* writes filtered documents
* writes excluded documents with reasons
* generates a filtering report

### Run thematic scoring

```bash
PYTHONPATH=src python -m changescout.cli score \
  --input artifacts/filtered.jsonl \
  --config config/scoring.yaml \
  --output artifacts/scored.jsonl \
  --report-output artifacts/scoring_report.json
```

This step:

* computes a thematic relevance score per document
* increases score for TLM geometry signals
* decreases score for soft change signals
* normalizes scores to range 0 to 1
* enriches documents with scoring signals
* writes scored documents
* generates a scoring report

### Build evaluation datasets

```bash
PYTHONPATH=src python scripts/build_evaluation_datasets.py
```

This step creates three frozen evaluation datasets from the expanded annotation dataset.

The expanded annotation dataset contains 348 manually reviewed sources.

The annotation labels are mapped to the derived `triage_class` field:

| tlm_relevant | review_required | triage_class |
|---|---|---|
| true | false | confirmed_relevant |
| false | true | needs_review |
| false | false | not_relevant |
| true | true | invalid |

The combination `tlm_relevant = true` and `review_required = true` is invalid.

Generated datasets:

| Dataset | Rows | Train | Test | Positive class | Excluded class |
|---|---:|---:|---:|---|---|
| strict_binary | 264 | 211 | 53 | confirmed_relevant | needs_review |
| actionable_binary | 348 | 278 | 70 | confirmed_relevant or needs_review | none |
| triage_3class | 348 | 278 | 70 | three class target | none |

The split column is frozen in each dataset.

The splits are stratified per target definition.

This means the task specific binary datasets and the triage dataset have stable splits, but their test rows are not guaranteed to be identical across all tasks.

For direct binary model evaluation, use the task specific binary datasets.

For fair method comparison across score, TF IDF, and LLM predictions, use the aligned comparison on the `triage_3class` test split.

### Evaluate deterministic score baseline

```bash
PYTHONPATH=src python scripts/evaluate_score_baseline.py
```

This step:

* evaluates the existing `thematic_score`
* performs threshold sweeps on the train split
* selects thresholds by train F1
* reports test metrics
* computes precision at N and recall at N

### Run classical text classifier evaluation

```bash
PYTHONPATH=src python scripts/evaluate_classical_text_classifier.py
```

This step:

* loads the frozen strict binary and actionable binary evaluation datasets
* uses the frozen train and test splits
* trains a TF IDF Logistic Regression classifier
* compares the classifier against the deterministic score baseline
* writes metrics, predictions, and a Markdown report

The classifier is a learned non LLM baseline.

It is not a final relevance authority.

### Run local LLM triage evaluation

```bash
PYTHONPATH=src python scripts/run_local_llm_triage.py \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --prompt-variant hierarchical

PYTHONPATH=src python scripts/evaluate_local_llm_triage.py \
  --predictions data/annotation/evaluation/local_llm/Qwen__Qwen2.5-7B-Instruct/hierarchical/llm_triage_predictions.jsonl
```

This step:

* loads the frozen three class triage test split
* runs a local Hugging Face instruct model
* uses the full source text without default truncation
* writes structured JSON predictions with triage class, labels, notes, and evidence
* evaluates strict binary, actionable binary, and three class triage metrics

Local LLM evaluation is experimental.

The current results show that local LLMs produce valid structured output, but they are more conservative than the TF IDF classifier.

### Compare local LLM runs

```bash
PYTHONPATH=src python scripts/compare_local_llm_runs.py
```

This step collects all local LLM evaluation reports and writes a model comparison table.

### Compare all evaluated methods on task specific binary splits

```bash
PYTHONPATH=src python scripts/compare_all_evaluation_methods.py
```

This step compares deterministic scoring, TF IDF Logistic Regression, and local LLM methods using their existing evaluation reports.

This report is useful for checking each task specific evaluation output.

It should not be used as the final cross method comparison if the underlying test records differ.

### Compare all evaluated methods on aligned triage test records

```bash
PYTHONPATH=src python scripts/evaluate_aligned_method_comparison.py
```

This step removes split alignment issues.

It evaluates all methods on the same frozen `triage_3class` test records.

For strict binary evaluation, `needs_review` records are excluded from the triage test split.

For actionable binary evaluation, `confirmed_relevant` and `needs_review` are mapped to positive.

The score threshold is selected on the corresponding triage train split.

The TF IDF classifier is trained on the corresponding triage train split.

Local LLM predictions are evaluated on the same triage test split without additional inference.

The aligned comparison is the preferred method comparison for reporting final findings.

### Run hybrid lead selection evaluation

```bash
PYTHONPATH=src python scripts/evaluate_hybrid_lead_selection.py   --llm-predictions data/annotation/evaluation/local_llm/Qwen__Qwen2.5-7B-Instruct/direct/llm_triage_predictions.jsonl   --output-dir data/annotation/evaluation/hybrid_lead_selection_qwen7b_direct

PYTHONPATH=src python scripts/compare_hybrid_lead_selection_runs.py
```

This step evaluates practical lead selection strategies on the aligned triage test split.

The target is actionable lead detection.

Positive actionable leads are `confirmed_relevant` and `needs_review`.

Evaluated modes include:

* `score_only`
* `tfidf_only`
* `llm_only`
* `score_or_tfidf`
* `hybrid_weighted`
* `hybrid_recall_guard`

The preferred current production oriented strategy is `score_or_tfidf` for high recall candidate selection plus a production feasible local LLM such as Qwen2.5 7B for evidence generation, triage notes, and optional priority support.

LLM predictions are not used as hard exclusion signals.


### Run LLM explainability output evaluation

First build explanation fields from existing LLM triage outputs.

```bash
PYTHONPATH=src python scripts/build_llm_explainability_leads.py
```

This step tests whether existing triage outputs are sufficient as explanation fields.

The current result shows that reusing triage outputs is not sufficient for reliable explanations.

Then run the dedicated explanation prompt on the selected top 50 `score_or_tfidf` leads.

```bash
PYTHONPATH=src python scripts/run_llm_explainability.py \
  --model-id Qwen/Qwen2.5-7B-Instruct
```

This step does not select or remove leads.

It generates review support fields for already selected leads:

* `evidence_type`
* `explanation_note`
* `evidence_snippet`
* `geometry_signal`
* `audit_warning`

The JSON keys and evidence type enum are stable machine readable fields.

The reviewer note and audit warning are generated in German.

The evidence snippet should stay in the original source wording.

### Run baseline lead generation

```bash
PYTHONPATH=src python scripts/generate_baseline_leads.py
```

This step:

* loads scored documents
* optionally joins classifier predictions if available
* includes documents with `thematic_score >= 0.10`
* creates reviewable lead records
* adds a text preview
* sorts leads deterministically
* writes lead outputs
* writes a lead generation report

### Run local location hinting

```bash
PYTHONPATH=src python scripts/add_location_hints_to_leads.py
```

This step:

* loads baseline leads
* loads a local reference file for simple location hints
* matches configured reference names against lead title and text
* attaches structured local location hints
* writes enriched lead outputs
* writes a location hinting report

Local location hints are review aids only.

They are not verified geocoding results.

### Run optional GeoAdmin location enrichment

```bash
PYTHONPATH=src python scripts/enrich_location_hints_geoadmin.py
```

This step:

* loads locally enriched leads
* builds short GeoAdmin Search API queries from local hints, titles, and limited text candidates
* uses the GeoAdmin Search API with `type=locations`
* stores query metadata and API responses in a local cache
* parses GeoAdmin hits into structured location hints
* ranks hits using canton context, API origin, object type, and API rank
* writes GeoAdmin enriched lead outputs
* writes a GeoAdmin location hinting report

GeoAdmin enrichment is optional.

API failure does not invalidate lead generation.

GeoAdmin hints are review aids only.

They may be missing, ambiguous, or noisy.

### Reproduce current baseline outputs

```bash
bash scripts/run.sh
```

This script reproduces the current MVP baseline outputs from existing discovery inputs.

It reprocesses AG and SG with the current HTML decoding and title extraction logic, rebuilds `artifacts/scored_annotation_pool.jsonl`, reruns scoring evaluation, trains the baseline classifier, regenerates baseline leads, and adds local location hints.

The script also performs basic quality checks, including expected pool size and encoding marker checks.

Each run writes run metadata and a full log to:

`artifacts/runs/<run_id>/run_metadata.json`

`artifacts/runs/<run_id>/logs/run.log`

If no run id is provided, the script creates a UTC timestamp based run id.

A custom run id can be set with:

```bash
RUN_ID=my_run_id bash scripts/run.sh
```

GeoAdmin Search API enrichment is optional and only runs when `ENABLE_GEOADMIN_ENRICHMENT=1` is set.

Run baseline reproduction with optional GeoAdmin enrichment:

```bash
RUN_ID=my_run_id ENABLE_GEOADMIN_ENRICHMENT=1 bash scripts/run.sh
```

GeoAdmin enrichment writes additional location hint outputs and best available coordinate candidates.

These coordinates are review aids only and are not verified project geometries.

## Output

### Frozen annotation and evaluation outputs

`data/annotation/labeled/annotation_dataset_expanded.csv`

Frozen expanded annotation dataset.

`data/annotation/labeled/annotation_dataset_expanded.jsonl`

Same dataset in JSONL format.

`data/annotation/labeled/annotation_dataset_expanded_report.json`

Machine readable build report for the expanded annotation dataset.

`data/annotation/labeled/annotation_dataset_quality_report.md`

Human readable quality report for the expanded annotation dataset.

`data/annotation/evaluation/strict_binary_dataset.csv`

Evaluation dataset for confirmed TLM relevance.

It excludes `needs_review` cases.

`data/annotation/evaluation/actionable_binary_dataset.csv`

Evaluation dataset for actionable lead detection.

It treats `confirmed_relevant` and `needs_review` as positive.

`data/annotation/evaluation/triage_3class_dataset.csv`

Evaluation dataset for three class triage.

The classes are `confirmed_relevant`, `needs_review`, and `not_relevant`.

`data/annotation/evaluation/evaluation_dataset_report.md`

Human readable report for generated evaluation datasets.

### Score baseline evaluation outputs

`data/annotation/evaluation/score_baseline/score_baseline_threshold_report.csv`

Threshold sweep for the deterministic thematic score.

`data/annotation/evaluation/score_baseline/score_baseline_at_n_report.csv`

Precision at N and recall at N report.

`data/annotation/evaluation/score_baseline/score_baseline_report.md`

Human readable score baseline evaluation report.

### Classical text classifier evaluation outputs

`data/annotation/evaluation/classical_text_classifier/classical_text_classifier_metrics.json`

Contains TF IDF Logistic Regression metrics for strict binary and actionable binary evaluation.

`data/annotation/evaluation/classical_text_classifier/classical_text_classifier_predictions.csv`

Contains test split predictions, probabilities, labels, scores, notes, and source metadata.

`data/annotation/evaluation/classical_text_classifier/classical_text_classifier_report.md`

Human readable comparison against the deterministic score baseline.

### Local LLM evaluation outputs

`data/annotation/evaluation/local_llm/<model>/<prompt_variant>/llm_triage_predictions.jsonl`

Contains one structured prediction per test source with:

* `triage_class`
* `tlm_relevant`
* `review_required`
* `change_type`
* `notes`
* `evidence`
* parse and schema validation fields
* runtime and input token metadata

`data/annotation/evaluation/local_llm/<model>/<prompt_variant>/llm_triage_run_report.json`

Contains runtime statistics for the local LLM run.

`data/annotation/evaluation/local_llm/<model>/<prompt_variant>/llm_triage_evaluation_report.md`

Human readable LLM evaluation report.

`data/annotation/evaluation/local_llm/comparison/local_llm_comparison.md`

Comparison of all local LLM runs.

`data/annotation/evaluation/local_llm/error_analysis/llm_triage_error_analysis.md`

Qualitative and quantitative error analysis of local LLM triage failures.

`data/annotation/evaluation/local_llm/error_analysis/llm_triage_error_summary.csv`

Aggregated counts of LLM triage error types by model and prompt variant.

`data/annotation/evaluation/local_llm/error_analysis/llm_triage_errors.csv`

Record level export of all LLM triage errors with gold labels, predictions, notes, evidence, and source metadata.

`data/annotation/evaluation/method_comparison/method_comparison_binary.md`

Comparison of deterministic scoring, classical ML, and local LLM methods based on existing task specific reports.

`data/annotation/evaluation/aligned_method_comparison/aligned_method_comparison.md`

Aligned comparison of deterministic scoring, TF IDF Logistic Regression, and local LLM methods on the same frozen triage test records.

This is the preferred report for final method comparison.

### Hybrid lead selection evaluation outputs

`data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_lead_selection_metrics.csv`

Precision at N, recall at N, false negatives, and workload reduction for each evaluated lead selection mode.

`data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_leads.csv`

Ranked lead exports for each evaluated lead selection mode.

`data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_eval_records.csv`

Merged evaluation records with thematic score, TF IDF probability, LLM triage output, and derived ranking signals.

`data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_lead_selection_report.md`

Human readable report for one hybrid lead selection run.

`data/annotation/evaluation/hybrid_lead_selection_comparison/hybrid_lead_selection_comparison.md`

Cross run comparison of hybrid lead selection strategies across evaluated LLM variants.

This is the preferred report for Issue 20.

`data/annotation/evaluation/hybrid_lead_selection_comparison/score_or_tfidf_top50_false_negatives.md`

False negative inspection for the recommended top 50 high recall strategy.


### LLM explainability outputs

`data/annotation/evaluation/llm_explainability/llm_explainability_leads.csv`

Lead export using existing local LLM triage outputs as explanation fields.

`data/annotation/evaluation/llm_explainability/llm_explainability_report.md`

Human readable report showing that existing triage outputs are not sufficient as a reliable explanation layer.

`data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated.jsonl`

Generated explanation output for selected leads using the dedicated explanation prompt.

Each record contains:

* `evidence_type`
* `explanation_note`
* `evidence_snippet`
* `geometry_signal`
* `audit_warning`
* parse status
* audit fields

`data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated.csv`

CSV version of the generated explanation output for manual inspection.

`data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated_report.md`

Human readable report for the dedicated explanation prompt.

Current top 50 result:

| Metric | Value |
|---|---:|
| parse success rate | 1.000 |
| missing evidence snippets | 0 |
| evidence snippets found exactly in source | 45 |
| explanations requiring manual check | 19 |

`data/annotation/evaluation/llm_explainability_generated/explainability_manual_review_notes.md`

Manual inspection notes for the generated explanations.

### Snapshot output

`artifacts/resolved_scope_snapshot.json`

Contains:

* scope configuration
* resolved active sources
* timestamp

### Discovery output

`artifacts/discovery.jsonl`

Each record contains:

* `source_id`
* `url`
* `discovered_at`

Optional:

* `base_url`
* `matched_pattern`

### Crawl output

`artifacts/crawl.jsonl`

Each record contains:

* `source_id`
* `url`
* `fetched_at`
* `status_code`
* `content_hash`
* `html_path`
* `error`
* `discovered_at`

### Cleaned output

`artifacts/cleaned.jsonl`

Each record contains:

* `document_id`
* `source_id`
* `url`
* `title`
* `clean_text`
* `language`
* `crawl_timestamp`
* `html_path`
* `clean_text_length`

### Excluded output

`artifacts/excluded.jsonl`

Contains documents filtered out during cleaning with reasons.

### Cleaning report

`artifacts/html_cleaning_report.json`

Contains:

* `total_documents`
* `included_documents`
* `excluded_documents`
* `inclusion_rate`
* `avg_clean_text_length`
* `exclusion_reasons`

### Filtered output

`artifacts/filtered.jsonl`

Each record contains:

* all fields from cleaned output
* `filter_signals`

### Filtered excluded output

`artifacts/filtered_excluded.jsonl`

Contains:

* excluded documents
* `exclusion_reason`
* `matched_rule`

### Filter report

`artifacts/filter_report.json`

Contains:

* `total_documents`
* `included_documents`
* `excluded_documents`
* `exclusion_reasons`

### Scored output

`artifacts/scored.jsonl`

Each record contains:

* all fields from filtered output
* `thematic_score`
* `scoring_signals`

`scoring_signals` includes:

* `rule_score`
* `rule_raw_score`
* `retrieval_score`
* `retrieval_raw_score`
* `structural_hits`
* `soft_hits`
* `title_structural_hits`
* `retrieval_query_terms`

### Scoring report

`artifacts/scoring_report.json`

Contains:

* `total_documents`
* `min_score`
* `max_score`
* `mean_score`
* `mean_rule_score`
* `mean_retrieval_score`
* `min_retrieval_raw_score`
* `max_retrieval_raw_score`
* `score_buckets`

### Lead outputs

`artifacts/leads.jsonl`

`artifacts/leads.csv`

Each lead contains:

* `document_id`
* `source_id`
* `url`
* `title`
* `thematic_score`
* `lead_reason`
* `classifier_prediction`
* `classifier_probability`
* `text_preview`

### Lead generation report

`artifacts/lead_generation_report.json`

Contains:

* `input_documents`
* `lead_count`
* `threshold`
* `min_score`
* `max_score`
* `mean_score`

### Local location hint outputs

`artifacts/leads_with_locations.jsonl`

`artifacts/leads_with_locations.csv`

Each enriched lead contains all lead fields plus:

* `location_hints`
* `location_hint_count`
* `location_hint_names`
* `municipality_hints`

Local location hints currently use a small local reference file.

They are mainly a deterministic offline fallback and testable baseline for the hinting workflow.

### Local location hinting report

`artifacts/location_hinting_report.json`

Contains:

* `total_records`
* `records_with_hints`
* `records_without_hints`
* `total_hints`
* `hint_type_counts`

### GeoAdmin location hint outputs

`artifacts/leads_with_geoadmin_locations.jsonl`

`artifacts/leads_with_geoadmin_locations.csv`

Each GeoAdmin enriched lead contains all local location hint fields plus:

* `geoadmin_preferred_canton`
* `geoadmin_location_hints`
* `geoadmin_location_hint_count`
* `geoadmin_query_count`
* `geoadmin_cache_hits`
* `geoadmin_cache_misses`
* `geoadmin_top_location_name`
* `geoadmin_location_queries`
* `geoadmin_best_location_name`
* `geoadmin_best_location_x`
* `geoadmin_best_location_y`
* `geoadmin_best_location_origin`
* `geoadmin_best_location_object_type`
* `geoadmin_best_location_query`
* `geoadmin_best_location_rank`

Structured GeoAdmin hints may include:

* `name`
* `object_type`
* `origin`
* `query`
* `rank`
* `x`
* `y`
* `detail`

GeoAdmin coordinates are optional review hints.

They are not confirmed lead locations.

### GeoAdmin location hinting report

`artifacts/geoadmin_location_hinting_report.json`

Contains:

* `total_records`
* `records_with_geoadmin_hints`
* `records_without_geoadmin_hints`
* `total_geoadmin_hints`
* `total_geoadmin_queries`
* `total_cache_hits`
* `total_cache_misses`
* `origin_counts`

### GeoAdmin API cache

`data/reference/geoadmin_search_cache.jsonl`

Contains cached GeoAdmin query records with:

* query parameters
* timestamp
* status
* error if present
* API response

The cache is local generated data and should not be versioned in Git.

### Run metadata output

`artifacts/runs/<run_id>/run_metadata.json`

Contains:

* `run_id`
* `status`
* `started_at`
* `updated_at`
* `ended_at`
* `failed_line`
* `geo_admin_enrichment_enabled`
* `git_commit`
* `git_status_short`
* `log_path`
* `config_paths`
* `input_paths`
* `report_paths`
* `output_paths`

The metadata file is written at run start, updated on success, and updated on failure when the shell failure trap is triggered.

### Run log output

`artifacts/runs/<run_id>/logs/run.log`

Contains the full console output of the MVP reproduction run.

The log is intended for debugging and traceability of a specific run.

### Monitoring summary output

`artifacts/monitoring_summary.json`

Contains a consolidated machine readable summary of the latest MVP reproduction run based on run metadata and available stage reports.

It includes:

* run status and metadata
* stage report availability
* cleaning metrics
* filtering metrics
* scoring metrics
* classification metrics
* lead generation metrics
* local location hinting metrics
* optional GeoAdmin hinting metrics
* warning messages for simple MVP checks

`artifacts/monitoring_summary.md`

Contains the same monitoring summary in a human readable format.

The monitoring summary is MVP observability only.

It is not a production alerting or drift detection system.

### HTML storage

Raw HTML files:

`data/crawling/<run_id>/<source_id>/<content_hash>.html`

## Pipeline stages

1. Scope definition
2. Discovery
3. Crawling
4. HTML cleaning
5. Hard filtering
6. Thematic scoring
7. Lead generation
8. Optional classification signals
9. Geographic hinting
10. Human review
11. MVP reproduction run
12. Evaluation dataset construction
13. Baseline evaluation
14. Local LLM evaluation
15. Task specific method comparison
16. Aligned method comparison
17. Hybrid lead selection evaluation
18. LLM explainability output evaluation

## Current discovery behavior

* fetches source HTML
* extracts anchor links
* normalizes URLs
* filters by include patterns
* excludes non HTML assets
* deduplicates URLs
* writes JSONL

## Current crawling behavior

* fetches URLs via HTTP
* decodes response content as UTF 8 when no explicit charset is provided
* stores raw HTML
* computes SHA256 hash
* writes structured crawl records
* logs failures
* continues on errors

## Current HTML cleaning behavior

* extracts title via fallback logic
* ignores technical JavaScript notice titles when better title candidates exist
* isolates main content container
* removes boilerplate elements
* extracts relevant text blocks
* normalizes text
* removes duplicate and low signal fragments
* applies basic language filtering
* produces normalized document schema

## Current scoring behavior

* computes rule based signals from keywords and regex patterns
* computes BM25 retrieval signals
* combines rule based and retrieval based scores
* preserves all filtered documents
* writes explanation fields for inspectability
* uses `config/scoring.yaml` version 10 as the frozen baseline

## Current classification behavior

* evaluates TF IDF Logistic Regression as the learned non LLM baseline
* uses title and full source text as model input
* does not use `notes`, `change_type`, `triage_class`, labels, `thematic_score`, or scoring signals as model input
* uses frozen train and test splits created during evaluation dataset construction
* compares results against the deterministic thematic score baseline
* treats classification as review support, not as final automatic relevance confirmation

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
| strict_binary | TF IDF Logistic Regression | 0.688 | 0.880 | 0.772 |
| actionable_binary | thematic_score | 0.750 | 0.857 | 0.800 |
| actionable_binary | TF IDF Logistic Regression | 0.771 | 0.881 | 0.822 |

The task specific binary split and aligned triage split answer different questions.

The task specific split is the original binary evaluation for each target.

The aligned split is the fairer cross method comparison because all methods are evaluated on the same test records.

## Current local LLM evaluation behavior

Local LLMs are evaluated on the frozen three class triage test split.

The same LLM output is mapped to:

* strict binary relevance
* actionable binary lead detection
* three class triage

Current evaluated local LLM runs on the triage test split:

| Method | Prompt | Strict F1 | Actionable F1 | Triage accuracy |
|---|---|---:|---:|---:|
| Qwen2.5 7B Instruct | hierarchical | 0.780 | 0.708 | 0.671 |
| Qwen2.5 7B Instruct | direct | 0.750 | 0.765 | 0.657 |
| Llama 3.1 8B Instruct | hierarchical | 0.667 | 0.706 | 0.586 |
| Qwen2.5 14B Instruct | hierarchical | 0.214 | 0.838 | 0.571 |

Aligned method comparison on the same triage test records:

| Task | Best method by F1 | Precision | Recall | F1 | Interpretation |
|---|---|---:|---:|---:|---|
| strict_binary | thematic_score | 0.957 | 0.880 | 0.917 | strongest confirmed relevance baseline on aligned records |
| actionable_binary | Qwen2.5 14B hierarchical | 0.969 | 0.738 | 0.838 | highest actionable F1, but lower recall than TF IDF and score |
| actionable_binary | TF IDF Logistic Regression | 0.771 | 0.881 | 0.822 | better recall for review queue coverage |
| actionable_binary | thematic_score | 0.750 | 0.857 | 0.800 | transparent high recall deterministic baseline |

Findings:

* all evaluated local LLM runs produced valid structured JSON output
* Qwen2.5 7B is very precise but too conservative for actionable lead detection
* Llama 3.1 8B performed below Qwen2.5 7B on this task
* Qwen2.5 14B improved actionable lead detection by assigning more positive cases to `needs_review`
* Qwen2.5 14B often degraded `confirmed_relevant` cases to `needs_review`, which hurts strict confirmed relevance
* on the aligned triage test split, Qwen2.5 14B achieved the highest actionable F1 among evaluated methods, but with lower actionable recall than TF IDF Logistic Regression and thematic_score
* on the aligned triage test split, thematic_score achieved the strongest strict binary F1
* the main LLM triage errors are `needs_review` mapped to `not_relevant`, `confirmed_relevant` mapped to `needs_review`, and `confirmed_relevant` mapped to `not_relevant`
* no evaluated local zero shot LLM is stable enough as a standalone three class triage classifier
* LLM predictions should not be used as hard exclusion signals
* local LLMs are more promising for evidence generation, precision filtering, and hybrid review support than for standalone lead discovery

## Current hybrid lead selection behavior

Hybrid lead selection is evaluated on the aligned triage test split.

The target is actionable lead detection.

Positive actionable leads are `confirmed_relevant` and `needs_review`.

Current evaluated modes:

* `score_only`
* `tfidf_only`
* `llm_only`
* `score_or_tfidf`
* `hybrid_weighted`
* `hybrid_recall_guard`

Best modes by review depth:

| Review depth | Best mode | LLM dependency | Precision at N | Recall at N | False negatives |
|---:|---|---|---:|---:|---:|
| 10 | `tfidf_only` | not applicable | 1.000 | 0.238 | 32 |
| 20 | `hybrid_recall_guard` | Qwen2.5 7B or 14B signal | 1.000 | 0.476 | 22 |
| 50 | `score_or_tfidf` | not applicable | 0.780 | 0.929 | 3 |
| 70 | `score_or_tfidf` | not applicable | 0.600 | 1.000 | 0 |

Findings:

* small review queues can benefit from LLM based prioritization
* broader high recall review queues benefit most from combining thematic_score and TF IDF probability
* Qwen2.5 14B is useful as an upper bound signal, but it is not the preferred production default
* Qwen2.5 7B variants are more production oriented and remain useful for evidence generation, triage notes, and optional priority support
* LLM `not_relevant` predictions should not be used as hard exclusion signals
* the recommended current strategy is `score_or_tfidf` candidate selection plus LLM based evidence and review support


## Current LLM explainability behavior

LLM explainability is evaluated downstream of hybrid lead selection.

It is applied to the top 50 `score_or_tfidf` leads from the production oriented Qwen2.5 7B direct setup.

The explanation layer does not select or remove leads.

It generates auditable review support fields.

Reusing existing LLM triage outputs as explanations was not sufficient.

It produced too many selected leads with `not_relevant` explanations and many records requiring manual checking.

A dedicated explanation prompt performs better.

Current top 50 generated explanation result:

| Metric | Value |
|---|---:|
| records | 50 |
| parse success rate | 1.000 |
| missing evidence snippets | 0 |
| evidence snippets found exactly in source | 45 |
| explanations requiring manual check | 19 |

Evidence type counts:

| Evidence type | Count |
|---|---:|
| confirmed_geometry | 22 |
| plausible_review_signal | 14 |
| no_geometry_evidence | 14 |

Findings:

* the dedicated explanation prompt is more useful than reusing triage outputs
* explanations improve lead reviewability but remain audit support
* non exact snippets, weak evidence, and `no_geometry_evidence` outputs are flagged for manual checking
* explanation output must not be treated as authoritative proof that TLM must be updated
* future prompt refinements should be evaluated separately to avoid optimizing on current test examples

## Current lead generation behavior

* includes documents with `thematic_score >= 0.10`
* attaches classifier prediction and probability if available
* adds a text preview for manual review
* sorts leads deterministically
* writes JSONL, CSV, and report outputs

## Current geographic hinting behavior

* local location hinting runs after lead generation
* local hints are matched from a simple reference CSV
* local matching is deterministic and offline
* GeoAdmin Search API enrichment is optional
* GeoAdmin queries are built from local hints, title candidates, and limited text fallback candidates
* GeoAdmin API responses are cached with query metadata
* GeoAdmin hits are parsed into structured hints
* GeoAdmin object types are extracted from API labels when available
* GeoAdmin hints are ranked using preferred canton, API origin, object type, API rank, and name
* GeoAdmin best location fields expose the first ranked hint with coordinates
* GeoAdmin coordinates are stored as optional review hints when available
* no lead is removed or promoted solely because of a geographic hint

## Current MVP reproduction behavior

* `scripts/run.sh` is the official MVP reproduction entry point
* the default run reproduces the offline baseline and local location hinting
* GeoAdmin enrichment is controlled by `ENABLE_GEOADMIN_ENRICHMENT=1`
* each run receives a `RUN_ID`
* if no `RUN_ID` is provided, a UTC timestamp based id is generated
* each run writes metadata to `artifacts/runs/<run_id>/run_metadata.json`
* each run writes a full log to `artifacts/runs/<run_id>/logs/run.log`
* failed runs write metadata with status `failed` when the failure trap is triggered
* the reproduction run coordinates existing stages and does not replace stage specific tests

## Current limitations

The MVP currently does not:

* confirm whether a lead corresponds to a finished or visible real world geometry change
* extract geographic entities robustly
* track documents across runs
* classify detailed change types as a reliable model target
* provide a production ready relevance classifier
* treat exported GeoAdmin best location coordinates as verified project geometry
* provide production grade orchestration, scheduling, retries, or alerting

Additional limitations:

* HTML cleaning prioritizes recall over precision
* the current scoring approach is keyword and pattern based and tuned to the MVP source mix
* the task specific binary split and aligned triage split produce different method rankings and must not be mixed without explanation
* on the aligned triage test split, thematic_score is strongest for strict confirmed relevance by F1
* on the aligned triage test split, Qwen2.5 14B has the highest actionable F1 but lower actionable recall than TF IDF Logistic Regression and thematic_score
* lead generation currently uses `thematic_score >= 0.10` as a recall oriented inclusion rule in the original MVP reproduction run
* local LLMs were evaluated zero shot and should not be interpreted as fine tuned domain models
* local LLMs are currently not stable enough for standalone three class triage
* LLM predictions of `not_relevant` should downgrade priority but should not remove candidates when score or TF IDF signals indicate actionable relevance
* LLM explanations improve reviewability but require audit flags and manual checking when evidence is weak or not exactly source matched
* lead output is intentionally broad and requires manual review
* geographic hints are optional review aids and not confirmed geocoding results
* GeoAdmin API labels and object types are used heuristically and are not treated as a stable authoritative enum
* GeoAdmin enrichment depends on online API availability unless cached responses already exist
* generalization to new cantons or source types is not guaranteed

## Project structure

* `src/changescout/` application code
* `config/` scope and source registry
* `tests/` automated tests
* `docs/` architecture and notes
* `artifacts/` generated outputs
* `data/crawling/` raw HTML storage
* `data/reference/` local generated reference and cache data