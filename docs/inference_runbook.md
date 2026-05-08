# ChangeScout Inference Runbook

This runbook explains how to add a new source registry or canton and run ChangeScout inference.

The goal is to make the repository usable for new official web sources without reading the code.

ChangeScout inference means:

1. discover URLs from a configured official source registry
2. crawl and clean the discovered pages
3. score and select review candidates
4. enrich selected leads with review aids
5. export a compact review package for manual inspection

A lead is not a confirmed TLM change.

A lead is a review candidate.

The final decision remains Human in the Loop.

## 1. Preconditions

Activate the environment:

```bash
cd /storage/homefs/lj11k048/changescout
source .venv/bin/activate
```

Run tests before changing configuration:

```bash
PYTHONPATH=src pytest -q
```

Check Git state:

```bash
git status
```

Use a clean Git state before adding a new registry.

## 2. Source registry concept

A source registry is a YAML file under:

`config/sources/<registry>.yaml`

Examples:

* `config/sources/zh.yaml`
* `config/sources/be.yaml`
* `config/sources/so_media.yaml`

A registry can contain one or many official source entries.

A source entry defines where discovery starts and which URLs are accepted.

Current operational discovery supports `crawl_type: html_pattern`.

`html_pattern` means:

1. fetch the `base_url`
2. extract all links
3. keep only links whose URL contains one of the configured `include_patterns`
4. remove binary assets
5. deduplicate canonical URLs

## 3. Create a new source registry

Create a new registry file.

Example placeholder for a new canton or source group:

```bash
cat > config/sources/xx.yaml <<'YAML'
version: 1

sources:
  - source_id: "xx_infrastructure_projects"
    name: "Canton XX Infrastructure Projects"
    base_url: "https://www.example-canton.ch/infrastructure/projects.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
    include_patterns:
      - "/infrastructure/projects/"
      - "/road-projects/"
YAML
```

Replace:

* `xx` with the registry id
* `source_id` with a stable lowercase id
* `name` with a human readable name
* `base_url` with the official entry page
* `include_patterns` with URL substrings that identify relevant subpages

## 4. Source registry rules

Use only official canton level or official agency sources.

Do not add social media.

Do not add private news sources unless the project scope is explicitly changed.

Use stable source ids.

Good source id examples:

* `be_region_berner_oberland`
* `zh_geplante_strassenprojekte`
* `so_media`

Avoid source ids that encode temporary decisions.

Bad source id examples:

* `test1`
* `newstuff`
* `maybe_good_source`

For each `html_pattern` source:

* `base_url` must be a valid HTTP or HTTPS URL
* `include_patterns` must not be empty
* `include_patterns` should be specific enough to avoid crawling unrelated pages
* `active` should be `true` only after a smoke test

## 5. Choose include patterns

Open the official page in a browser.

Inspect the links to real project detail pages.

Use stable URL fragments.

Example:

```text
https://www.zh.ch/de/planen-bauen/tiefbau/geplante-strassenprojekte/strassenprojekt-affoltern-am-albis.html
```

Useful include patterns:

```text
/geplante-strassenprojekte/strassenprojekt-
/geplante-strassenprojekte/geplantes-strassenprojekt-
/geplante-strassenprojekte/umfahrung-
/geplante-strassenprojekte/ortsdurchfahrt
```

Avoid overly broad patterns:

```text
/de/
/news/
/detail/
```

Broad patterns create noisy runs and slow inference.

## 6. Optional scope config

The scoped operational CLI can take `--source-registry` and `--canton-id` directly.

For manual snapshot checks, `config/scope.yaml` can be updated.

Example:

```yaml
version: 1
canton_id: "xx"
languages:
  - "de"
time_window_days: 30
source_registry: "xx"
source_policy: "official_canton_only"
```

The source registry value maps to:

`config/sources/xx.yaml`

## 7. Validate the source registry

Before running discovery or full inference, validate the registry.

```bash
PYTHONPATH=src python -m changescout.cli validate-registry \
  --config-dir config \
  --source-registry xx
```

To write validation artifacts:

```bash
PYTHONPATH=src python -m changescout.cli validate-registry \
  --config-dir config \
  --source-registry xx \
  --output-dir artifacts/registry_validation/xx_001
```

To validate and run a discovery smoke test:

```bash
PYTHONPATH=src python -m changescout.cli validate-registry \
  --config-dir config \
  --source-registry xx \
  --smoke-discovery \
  --output-dir artifacts/registry_validation/xx_001 \
  --timeout-seconds 10
```

The command writes:

```text
artifacts/registry_validation/<run_id>/
  registry_validation_report.json
  discovery_smoke.jsonl
  discovery_smoke_report.json
```

Validation checks include:

* registry file exists
* `sources` is a non empty list
* required source fields exist
* `source_id` values are unique
* `base_url` is a valid HTTP or HTTPS URL
* `crawl_type` is supported
* `html_pattern` sources define `include_patterns`
* active sources exist
* overly broad include patterns are reported as warnings

## 7. Snapshot check

Run:

```bash
PYTHONPATH=src python -m changescout.cli snapshot \
  --config-dir config \
  --snapshot-dir artifacts/tmp_scope_check
```

Inspect:

```bash
cat artifacts/tmp_scope_check/resolved_scope_snapshot.json
```

Check:

* correct canton id
* correct source registry
* expected active sources
* expected base URLs
* expected include patterns

Remove the temporary snapshot after inspection:

```bash
rm -rf artifacts/tmp_scope_check
```

## 8. Discovery smoke test

Run discovery only.

```bash
PYTHONPATH=src python -m changescout.cli discover \
  --config-dir config \
  --output artifacts/discovery_xx_smoke.jsonl
```

Inspect record count:

```bash
wc -l artifacts/discovery_xx_smoke.jsonl
head -5 artifacts/discovery_xx_smoke.jsonl
```

Expected result:

* more than zero records for a useful registry
* URLs belong to the expected official source
* URLs look like detail pages
* no PDF, image, Word, Excel or ZIP URLs

If the output is empty:

1. check that the source is active
2. check that `crawl_type` is `html_pattern`
3. check that `include_patterns` match actual links
4. check whether the page builds links dynamically with JavaScript

If too many unrelated URLs appear:

1. make `include_patterns` stricter
2. split the source into multiple specific source entries
3. avoid generic path fragments

Clean smoke output after inspection:

```bash
rm -f artifacts/discovery_xx_smoke.jsonl
```

## 9. Train or verify TF IDF artifact

The recommended `score_or_tfidf` inference mode requires a TF IDF model artifact.

Check whether it exists:

```bash
find data/models/tfidf_actionable/tfidf_actionable_v1 -maxdepth 1 -type f | sort
```

Expected files:

```text
model.joblib
metadata.json
test_predictions.csv
```

If missing, train it:

```bash
PYTHONPATH=src python scripts/ml/train_operational_tfidf.py \
  --dataset data/annotation/evaluation/triage_3class_dataset.csv \
  --output-dir data/models/tfidf_actionable/tfidf_actionable_v1 \
  --model-version tfidf_actionable_v1
```

Inspect metadata:

```bash
cat data/models/tfidf_actionable/tfidf_actionable_v1/metadata.json
```

## Standard inference preset

For regular inference, use the concise preset command.

It runs the recommended high recall setup:

* scoped operational run
* `score_or_tfidf` candidate selection
* default TF IDF artifact
* local location hinting
* optional GeoAdmin enrichment

```bash
PYTHONPATH=src python -m changescout.cli infer \
  --source-registry be \
  --canton-id be \
  --run-id be_infer_001
```

With GeoAdmin enrichment:

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

## 10. Run score only inference

Use this for the first full run on a new source registry.

It avoids TF IDF dependency and shows whether the deterministic pipeline works.

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry xx \
  --canton-id xx \
  --run-id xx_score_only_001 \
  --output-root artifacts/runs \
  --html-root data/crawling \
  --lead-threshold 0.10 \
  --candidate-selection-mode score_only \
  --timeout-seconds 10
```

Inspect outputs:

```bash
find artifacts/runs/xx_score_only_001 -maxdepth 3 -type f | sort
cat artifacts/runs/xx_score_only_001/metadata/run_metadata.json
cat artifacts/runs/xx_score_only_001/reports/lead_generation_report.json
```

## 11. Run recommended hybrid inference

Use this after the score only run succeeds.

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry xx \
  --canton-id xx \
  --run-id xx_hybrid_001 \
  --output-root artifacts/runs \
  --html-root data/crawling \
  --lead-threshold 0.10 \
  --tfidf-threshold 0.50 \
  --candidate-selection-mode score_or_tfidf \
  --tfidf-model-artifact data/models/tfidf_actionable/tfidf_actionable_v1 \
  --timeout-seconds 10
```

Inspect TF IDF report:

```bash
cat artifacts/runs/xx_hybrid_001/reports/tfidf_inference_report.json
```

Inspect candidate selection report:

```bash
cat artifacts/runs/xx_hybrid_001/reports/lead_generation_report.json
```

Inspect top leads:

```bash
python - <<'PY'
import json
from pathlib import Path

path = Path("artifacts/runs/xx_hybrid_001/leads.jsonl")

for index, line in enumerate(path.open(encoding="utf-8")):
    if index >= 20:
        break
    record = json.loads(line)
    print(
        record.get("rank"),
        record.get("title"),
        record.get("selection_score"),
        record.get("thematic_score"),
        record.get("tfidf_actionable_probability"),
        record.get("selection_reason"),
    )
PY
```

## 12. Run hybrid inference with GeoAdmin

GeoAdmin enrichment is optional.

It runs only on selected leads.

GeoAdmin hints are review aids only.

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry xx \
  --canton-id xx \
  --run-id xx_hybrid_geoadmin_001 \
  --output-root artifacts/runs \
  --html-root data/crawling \
  --lead-threshold 0.10 \
  --tfidf-threshold 0.50 \
  --candidate-selection-mode score_or_tfidf \
  --tfidf-model-artifact data/models/tfidf_actionable/tfidf_actionable_v1 \
  --enable-geoadmin-enrichment \
  --timeout-seconds 10
```

Inspect GeoAdmin report:

```bash
cat artifacts/runs/xx_hybrid_geoadmin_001/reports/geoadmin_location_hinting_report.json
```

Inspect GeoAdmin examples:

```bash
python - <<'PY'
import json
from pathlib import Path

path = Path("artifacts/runs/xx_hybrid_geoadmin_001/leads_with_geoadmin_locations.jsonl")

for index, line in enumerate(path.open(encoding="utf-8")):
    if index >= 10:
        break
    record = json.loads(line)
    print(
        record.get("rank"),
        record.get("title"),
        record.get("geoadmin_top_location_name"),
        record.get("geoadmin_location_hint_count"),
    )
PY
```

## 13. Build review export

Build the reviewer facing package.

```bash
PYTHONPATH=src python scripts/operational/build_review_export.py \
  --run-dir artifacts/runs/xx_hybrid_geoadmin_001 \
  --top-n 30
```

Inspect:

```bash
find artifacts/runs/xx_hybrid_geoadmin_001/review -maxdepth 1 -type f | sort
cat artifacts/runs/xx_hybrid_geoadmin_001/review/review_export_report.json
sed -n '1,120p' artifacts/runs/xx_hybrid_geoadmin_001/review/review_summary.md
```

Open the CSV:

`artifacts/runs/xx_hybrid_geoadmin_001/review/review_leads.csv`

Important columns:

* `rank`
* `title`
* `url`
* `source_id`
* `duplicate_count`
* `duplicate_source_ids`
* `selection_score`
* `thematic_score`
* `tfidf_actionable_probability`
* `selection_reason`
* `geoadmin_top_location_name`
* `geoadmin_best_location_x`
* `geoadmin_best_location_y`
* `text_preview`

## Optional scoped LLM explainability

LLM explainability is optional.

It requires local Hugging Face model access and suitable GPU resources.

Run it only after candidate selection.

The LLM explains selected leads.

It does not select or remove leads.

```bash
PYTHONPATH=src python scripts/ml/run_scoped_llm_explainability.py \
  --run-dir artifacts/runs/xx_hybrid_geoadmin_001 \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --max-records 10
```

For a small demo run, limit the number of records:

```bash
PYTHONPATH=src python scripts/ml/run_scoped_llm_explainability.py \
  --run-dir artifacts/runs/xx_hybrid_geoadmin_001 \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --max-records 3 \
  --max-new-tokens 384
```

This writes:

```text
artifacts/runs/<run_id>/leads_with_llm_explanations.jsonl
artifacts/runs/<run_id>/leads_with_llm_explanations.csv
artifacts/runs/<run_id>/reports/llm_explainability_report.json
artifacts/runs/<run_id>/reports/llm_explainability_report.md
```

Then rebuild the review export:

```bash
PYTHONPATH=src python scripts/operational/build_review_export.py \
  --run-dir artifacts/runs/xx_hybrid_geoadmin_001 \
  --top-n 30
```

The review export prefers `leads_with_llm_explanations.jsonl` when it exists.

LLM output fields include:

* `evidence_type`
* `explanation_note`
* `evidence_snippet`
* `geometry_signal`
* `audit_warning`
* `parse_success`
* `evidence_snippet_found_in_source`
* `requires_manual_check`

The LLM report includes:

* model id
* input lead file
* output lead file
* record count
* parse success rate
* evidence type counts
* evidence snippets found in source
* missing evidence snippets
* records requiring manual check

Weak or unsupported explanations are audit flagged.

LLM outputs are never hard exclusion signals.

## Build inference QA report

After an inference run, build a lightweight QA report before manual review.

```bash
PYTHONPATH=src python scripts/operational/build_inference_qa_report.py \
  --run-dir artifacts/runs/xx_hybrid_geoadmin_001
```

The QA report writes:

```text
artifacts/runs/<run_id>/reports/inference_qa_report.json
artifacts/runs/<run_id>/reports/inference_qa_report.md
```

The QA report checks:

* lead count
* missing URLs
* missing titles
* empty text previews
* missing TF IDF probabilities in hybrid mode
* missing `selection_reason`
* duplicate canonical URLs
* local location hint counts
* GeoAdmin hint counts

The QA report is a sanity check.

It does not evaluate model quality.

It does not confirm TLM relevance.

## 14. Build monitoring summary

```bash
PYTHONPATH=src python scripts/operational/build_monitoring_summary.py \
  --run-id xx_hybrid_geoadmin_001
```

Inspect:

```bash
cat artifacts/runs/xx_hybrid_geoadmin_001/monitoring_summary.md
```

## 15. Interpret outputs

Use these checks:

| Check | Good sign | Problem sign |
|---|---|---|
| discovery count | expected number of project pages | zero or hundreds of unrelated pages |
| crawl success | most pages status 200 | many errors |
| cleaning inclusion | most project pages included | many excluded as low text |
| lead count | smaller than input for noisy sources | all documents selected for noisy source |
| GeoAdmin hints | plausible place hints | broad regions or unrelated names |
| review export | readable top leads | duplicate projects or missing URLs |

A broad curated project source may legitimately produce many leads.

A noisy media source should usually produce fewer leads than input documents.

## 16. Typical debugging

### Discovery returns zero URLs

Check:

```bash
cat config/sources/xx.yaml
```

Common causes:

* source is inactive
* wrong `crawl_type`
* include patterns do not match actual URLs
* page uses JavaScript generated links

### Discovery returns too many URLs

Make include patterns stricter.

Avoid broad fragments like:

```text
/de/
/news/
/detail/
```

### Crawl fails

Check:

```bash
cat artifacts/runs/<run_id>/reports/crawl_report.json
tail -80 artifacts/runs/<run_id>/logs/run.log
```

Common causes:

* source blocks requests
* timeout too low
* invalid URLs
* server errors

### HTML cleaning excludes many pages

Check:

```bash
cat artifacts/runs/<run_id>/reports/cleaning_report.json
head -3 artifacts/runs/<run_id>/excluded.jsonl
```

Common causes:

* main content selector does not capture the content
* page is mostly JavaScript
* text is too short after boilerplate removal

### Hybrid mode fails

Check that the model artifact exists:

```bash
find data/models/tfidf_actionable/tfidf_actionable_v1 -maxdepth 1 -type f | sort
```

Check command includes:

```text
--candidate-selection-mode score_or_tfidf
--tfidf-model-artifact data/models/tfidf_actionable/tfidf_actionable_v1
```

### GeoAdmin output is noisy

GeoAdmin hints are optional.

They can be missing, ambiguous, or wrong.

Inspect:

```bash
cat artifacts/runs/<run_id>/reports/geoadmin_location_hinting_report.json
```

Use GeoAdmin only as a review aid.

Never treat coordinates as verified project geometry.

## 17. Cleanup test runs

Remove temporary run artifacts:

```bash
rm -rf artifacts/runs/xx_score_only_001 data/crawling/xx_score_only_001
rm -rf artifacts/runs/xx_hybrid_001 data/crawling/xx_hybrid_001
rm -rf artifacts/runs/xx_hybrid_geoadmin_001 data/crawling/xx_hybrid_geoadmin_001
```

Do not delete frozen evaluation artifacts under:

`data/annotation/evaluation/`

## 18. Commit a new source registry

After a successful inference smoke test:

```bash
git status --short
git add config/sources/xx.yaml
git commit -m "Add XX source registry"
git push
```

If you changed docs or source code, commit them separately from the source registry.

## 19. Existing registry example

Bern standard preset inference:

```bash
PYTHONPATH=src python -m changescout.cli infer \
  --source-registry be \
  --canton-id be \
  --run-id be_infer_geoadmin_001 \
  --enable-geoadmin-enrichment

PYTHONPATH=src python scripts/operational/build_review_export.py \
  --run-dir artifacts/runs/be_infer_geoadmin_001 \
  --top-n 30

PYTHONPATH=src python scripts/operational/build_monitoring_summary.py \
  --run-id be_infer_geoadmin_001
```

Full command equivalent:

Bern hybrid GeoAdmin inference:

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

PYTHONPATH=src python scripts/operational/build_review_export.py \
  --run-dir artifacts/runs/be_hybrid_geoadmin_001 \
  --top-n 30

PYTHONPATH=src python scripts/operational/build_monitoring_summary.py \
  --run-id be_hybrid_geoadmin_001
```

Inspect:

```bash
cat artifacts/runs/be_hybrid_geoadmin_001/review/review_summary.md
cat artifacts/runs/be_hybrid_geoadmin_001/monitoring_summary.md
```

## 20. New registry placeholder example

```bash
cat > config/sources/xx.yaml <<'YAML'
version: 1

sources:
  - source_id: "xx_official_projects"
    name: "Canton XX Official Projects"
    base_url: "https://www.example-canton.ch/projects.html"
    crawl_type: "html_pattern"
    crawl_frequency_hours: 168
    active: true
    include_patterns:
      - "/projects/"
      - "/infrastructure/"
YAML
```

Then run:

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry xx \
  --canton-id xx \
  --run-id xx_hybrid_geoadmin_001 \
  --output-root artifacts/runs \
  --html-root data/crawling \
  --lead-threshold 0.10 \
  --tfidf-threshold 0.50 \
  --candidate-selection-mode score_or_tfidf \
  --tfidf-model-artifact data/models/tfidf_actionable/tfidf_actionable_v1 \
  --enable-geoadmin-enrichment \
  --timeout-seconds 10

PYTHONPATH=src python scripts/operational/build_review_export.py \
  --run-dir artifacts/runs/xx_hybrid_geoadmin_001 \
  --top-n 30
```

## 21. Final rule

ChangeScout inference produces review candidates.

It does not confirm a TLM update.

It does not verify project geometry.

It does not replace expert judgement.
