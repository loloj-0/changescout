# Script Inventory

This document classifies scripts by workflow responsibility.

ChangeScout currently has three separate workflow types:

1. operational registry scoped runs
2. MVP baseline reproduction
3. annotation and evaluation workflows

Operational code should move into `src/changescout` modules and be exposed through `python -m changescout.cli`.

Scripts are allowed for evaluation, annotation, reporting, and historical reproduction, but their workflow boundary must be explicit.

## Operational entry points

| Script or command | Role | Status |
|---|---|---|
| `PYTHONPATH=src python -m changescout.cli run` | Registry scoped operational pipeline from source config to leads | current operational entry point |
| `PYTHONPATH=src python -m changescout.cli snapshot` | Resolve configured source scope and write snapshot | supported utility |
| `PYTHONPATH=src python -m changescout.cli discover` | Run discovery only | supported stage utility |
| `PYTHONPATH=src python -m changescout.cli crawl` | Run crawling only | supported stage utility |
| `PYTHONPATH=src python -m changescout.cli filter` | Run hard filtering only | supported stage utility |
| `PYTHONPATH=src python -m changescout.cli score` | Run thematic scoring only | supported stage utility |

## MVP reproduction workflow

These scripts reproduce the historical MVP baseline and evaluated annotation pool.

They may contain hardcoded artifact paths by design.

They are not generic operational runners.

| Script | Role | Notes |
|---|---|---|
| `scripts/run.sh` | Historical MVP baseline reproduction | Combines existing ZH and BE artifacts with rerun AG and SG processing |
| `scripts/generate_baseline_leads.py` | Generate baseline leads from `artifacts/scored_annotation_pool.jsonl` | Reproduction helper |
| `scripts/add_location_hints_to_leads.py` | Add local location hints to global baseline leads | Reproduction helper and candidate for scoped operational reuse |
| `scripts/enrich_location_hints_geoadmin.py` | Add optional GeoAdmin hints to global location enriched leads | Reproduction helper and candidate for scoped operational reuse |
| `scripts/build_monitoring_summary.py` | Build monitoring summary from run metadata and reports | Needs adaptation for scoped operational metadata layout |

## Annotation tooling

| Script | Role | Status |
|---|---|---|
| `scripts/run_annotation_expansion.sh` | Run discovery, crawling, cleaning, filtering, and scoring for additional registries used in annotation expansion | historical annotation expansion workflow |
| `scripts/test_annotation_expansion_discovery.sh` | Discovery smoke test for annotation expansion registries | helper |
| `scripts/build_expanded_annotation_dataset.py` | Build frozen expanded annotation dataset from reviewed Excel files | current annotation build |
| `scripts/report_annotation_dataset.py` | Build quality and distribution reports for annotation dataset | current annotation QA |

## Evaluation dataset building

| Script | Role | Status |
|---|---|---|
| `scripts/build_evaluation_datasets.py` | Build strict binary, actionable binary, and triage 3 class datasets | current evaluation build |
| `scripts/evaluate_score_baseline.py` | Evaluate deterministic thematic score on frozen evaluation datasets | current evaluation |
| `scripts/evaluate_classical_text_classifier.py` | Evaluate TF IDF Logistic Regression baseline | current evaluation |
| `scripts/evaluate_scoring_against_annotations.py` | Older scoring evaluation against annotation file and scored annotation pool | legacy candidate |
| `scripts/train_baseline_classifier.py` | Older baseline classifier workflow | legacy candidate |

## Method comparison

| Script | Role | Status |
|---|---|---|
| `scripts/compare_all_evaluation_methods.py` | Compare methods on task specific binary evaluation outputs | secondary comparison |
| `scripts/evaluate_aligned_method_comparison.py` | Compare score, TF IDF, and LLMs on aligned triage test records | preferred method comparison |
| `scripts/evaluate_hybrid_lead_selection.py` | Evaluate hybrid review queue strategies on aligned triage test records | current evaluation and future operational design reference |
| `scripts/compare_hybrid_lead_selection_runs.py` | Compare hybrid lead selection across LLM variants | current evaluation comparison |

## Local LLM evaluation

| Script | Role | Status |
|---|---|---|
| `scripts/run_local_llm_triage.py` | Run local Hugging Face LLM triage on frozen test split | current LLM evaluation |
| `scripts/evaluate_local_llm_triage.py` | Evaluate local LLM triage predictions | current LLM evaluation |
| `scripts/compare_local_llm_runs.py` | Compare local LLM evaluation reports | current LLM comparison |
| `scripts/build_llm_explainability_leads.py` | Build explanation fields from existing LLM triage outputs | evaluation experiment, not preferred for production |
| `scripts/run_llm_explainability.py` | Run dedicated LLM explanation prompt on selected evaluation leads | current explainability evaluation |

## Evaluation report package

| Script | Role | Status |
|---|---|---|
| `scripts/build_evaluation_report_package.py` | Build consolidated report ready evaluation package | current reporting |

## Refactor candidates

The following scripts should be converted into reusable modules or thin wrappers before being used by the operational runner:

| Script | Reason |
|---|---|
| `scripts/add_location_hints_to_leads.py` | Uses useful module logic but hardcodes global artifact paths |
| `scripts/enrich_location_hints_geoadmin.py` | Useful for operational lead enrichment but hardcodes global artifact paths |
| `scripts/build_monitoring_summary.py` | Useful, but current metadata discovery assumes old run metadata layout |
| `scripts/evaluate_aligned_method_comparison.py` | Contains TF IDF model logic that may later be extracted for operational inference |
| `scripts/evaluate_hybrid_lead_selection.py` | Contains score_or_tfidf logic that may later inform operational candidate selection |

## Deprecated candidates

Do not delete yet.

Mark as legacy until all reports and reproduction workflows no longer depend on them.

| Script | Reason |
|---|---|
| `scripts/evaluate_scoring_against_annotations.py` | Older evaluation path based on global scored annotation pool |
| `scripts/train_baseline_classifier.py` | Older classifier workflow, superseded by `evaluate_classical_text_classifier.py` for current evaluation |
