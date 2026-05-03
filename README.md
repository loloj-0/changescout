# ChangeScout

ChangeScout is a deterministic monitoring pipeline for canton scoped observation of official web sources.

## Initial MVP goal

The first MVP generates deterministic leads for potential TLM relevant real world changes within one canton.

The system resolves the same active source set from the same config and produces reproducible candidate leads from manually curated official canton level sources.

The MVP focuses on identifying candidate documents that may indicate TLM relevant geometry changes, such as new roads, extensions, bridges, junction redesigns, new paths, or other network relevant modifications.

The MVP does not try to automatically confirm whether a lead already corresponds to a finished or visible geometry change.

Manual validation remains part of the workflow.

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

### Run baseline classification

```bash
PYTHONPATH=src python scripts/train_baseline_classifier.py
```

This step:

* loads the reviewed annotation dataset
* joins annotations with scored documents by URL
* excludes review cases from core training and evaluation
* trains a TF IDF Logistic Regression baseline classifier
* compares the classifier against the scoring baseline
* writes train and test splits
* writes predictions
* writes classifier metrics

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

## Output

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

### Baseline classifier outputs

`data/annotation/evaluation/baseline_classifier_metrics.json`

Contains:

* dataset size
* missing scored records
* train and test split sizes
* classifier precision, recall, F1
* classifier confusion matrix counts
* scoring baseline comparison at threshold `0.10`

`data/annotation/evaluation/baseline_classifier_predictions.csv`

Contains test set predictions with:

* `document_id`
* `source_id`
* `url`
* `title`
* `tlm_relevant`
* `thematic_score`
* `classifier_prediction`
* `classifier_probability`

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
7. Classification
8. Lead generation

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

* uses `tlm_relevant` as the target label
* excludes `review_required = true` records from core training and evaluation
* trains a TF IDF Logistic Regression baseline model
* compares model metrics against scoring baseline at threshold `0.10`
* treats records removed before scoring as missing scored records and excludes them from classifier training

## Current lead generation behavior

* includes documents with `thematic_score >= 0.10`
* attaches classifier prediction and probability if available
* adds a text preview for manual review
* sorts leads deterministically
* writes JSONL, CSV, and report outputs

## Current limitations

The MVP currently does not:

* confirm whether a lead corresponds to a finished or visible real world geometry change
* extract geographic entities robustly
* track documents across runs
* classify detailed change types as a reliable model target
* provide a production ready relevance classifier

Additional limitations:

* HTML cleaning prioritizes recall over precision
* the current scoring approach is keyword and pattern based and tuned to the MVP source mix
* the baseline classifier is a first TF IDF Logistic Regression model and does not yet outperform the high recall scoring baseline
* lead generation currently uses `thematic_score >= 0.10` as a recall oriented inclusion rule
* lead output is intentionally broad and requires manual review
* generalization to new cantons or source types is not guaranteed

## Project structure

* `src/changescout/` application code
* `config/` scope and source registry
* `tests/` automated tests
* `docs/` architecture and notes
* `artifacts/` generated outputs
* `data/crawling/` raw HTML storage