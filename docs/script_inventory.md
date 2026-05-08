# Script Inventory

This document classifies scripts by workflow responsibility after the repository structure refactor.

ChangeScout separates reusable application logic from workflow scripts.

Application logic lives in `src/changescout/`.

Scripts are thin workflow entry points for operational runs, annotation, evaluation, model experiments, and legacy reproduction.

## Preferred entry points

| Command or script | Role | Status |
|---|---|---|
| `PYTHONPATH=src python -m changescout.cli infer` | Standard scoped inference preset using `score_or_tfidf` and the default TF IDF artifact. | preferred operational entry point |
| `PYTHONPATH=src python -m changescout.cli run` | Configurable scoped operational pipeline. | preferred full operational entry point |
| `PYTHONPATH=src python -m changescout.cli validate-registry` | Validate a source registry and optionally run a discovery smoke test. | supported utility |
| `PYTHONPATH=src python -m changescout.cli snapshot` | Resolve the active scope and source registry. | supported utility |
| `PYTHONPATH=src python -m changescout.cli discover` | Run discovery only. | supported stage utility |
| `PYTHONPATH=src python -m changescout.cli crawl` | Run crawling only. | supported stage utility |
| `PYTHONPATH=src python -m changescout.cli filter` | Run hard filtering only. | supported stage utility |
| `PYTHONPATH=src python -m changescout.cli score` | Run thematic scoring only. | supported stage utility |

## Repository script groups

| Directory | Responsibility | Boundary |
|---|---|---|
| `scripts/operational/` | Helpers for scoped operational runs and review exports. | May read and write `artifacts/runs/<run_id>/`. |
| `scripts/annotation/` | Annotation dataset construction and annotation expansion workflows. | Builds curated annotation data from reviewed inputs. |
| `scripts/evaluation/` | Evaluation dataset creation, method evaluation, comparison, and report package generation. | Reads frozen datasets from `data/annotation/evaluation/` and writes result artifacts to `results/evaluation/`. |
| `scripts/ml/` | Model training and local LLM experiment scripts. | Produces model artifacts or evaluation outputs. |
| `scripts/legacy/` | Historical MVP reproduction helpers with global artifact paths. | Kept for traceability, not part of scoped operational inference. |

## Operational scripts

| Script | Role | Status |
|---|---|---|
| `scripts/operational/build_review_export.py` | Build reviewer facing CSV and Markdown export from a scoped run. | current operational helper |
| `scripts/operational/build_monitoring_summary.py` | Build a scoped monitoring summary from run metadata and reports. | current operational helper |
| `scripts/operational/build_inference_qa_report.py` | Build QA checks for an inference run before manual review. | current operational helper |
| `scripts/operational/run_tfidf_inference.py` | Apply an existing TF IDF actionable artifact to scored records. | current operational helper |
| `scripts/operational/add_location_hints_to_leads.py` | Add local deterministic location hints to leads. | reusable helper, still supports explicit file paths |
| `scripts/operational/enrich_location_hints_geoadmin.py` | Add optional GeoAdmin location hints to leads. | reusable helper, optional online enrichment |
| `scripts/operational/run.sh` | Historical MVP baseline reproduction wrapper. | legacy style, kept for reproducibility |

## Annotation scripts

| Script | Role | Status |
|---|---|---|
| `scripts/annotation/build_expanded_annotation_dataset.py` | Build the frozen expanded annotation dataset from reviewed Excel files. | current annotation build |
| `scripts/annotation/report_annotation_dataset.py` | Build annotation quality and distribution reports. | current annotation QA |
| `scripts/annotation/run_annotation_expansion.sh` | Run discovery, crawling, cleaning, filtering, and scoring for annotation expansion registries. | historical annotation expansion workflow |
| `scripts/annotation/test_annotation_expansion_discovery.sh` | Smoke test discovery for annotation expansion registries. | helper |

## Evaluation scripts

| Script | Role | Status |
|---|---|---|
| `scripts/evaluation/build_evaluation_datasets.py` | Build strict binary, actionable binary, and three class triage datasets. | current evaluation build |
| `scripts/evaluation/evaluate_score_baseline.py` | Evaluate deterministic thematic score on frozen evaluation datasets. | current evaluation |
| `scripts/evaluation/evaluate_classical_text_classifier.py` | Evaluate TF IDF Logistic Regression baseline. | current evaluation |
| `scripts/evaluation/evaluate_aligned_method_comparison.py` | Compare score, TF IDF, and LLMs on aligned triage test records. | preferred method comparison |
| `scripts/evaluation/evaluate_hybrid_lead_selection.py` | Evaluate hybrid review queue strategies. | current evaluation and operational design reference |
| `scripts/evaluation/compare_hybrid_lead_selection_runs.py` | Compare hybrid lead selection across LLM variants. | current comparison |
| `scripts/evaluation/evaluate_local_llm_triage.py` | Evaluate local LLM triage predictions. | current evaluation |
| `scripts/evaluation/compare_local_llm_runs.py` | Compare local LLM evaluation reports. | current comparison |
| `scripts/evaluation/compare_all_evaluation_methods.py` | Compare task specific binary evaluation outputs. | secondary comparison |
| `scripts/evaluation/build_evaluation_report_package.py` | Build consolidated report ready evaluation package. | current reporting |
| `scripts/evaluation/evaluate_scoring_against_annotations.py` | Older scoring evaluation against the global scored annotation pool. | legacy candidate |

## ML scripts

| Script | Role | Status |
|---|---|---|
| `scripts/ml/train_operational_tfidf.py` | Train the operational TF IDF actionable artifact. | current model artifact build |
| `scripts/ml/run_local_llm_triage.py` | Run local Hugging Face LLM triage on the frozen test split. | current LLM evaluation |
| `scripts/ml/run_scoped_llm_explainability.py` | Generate LLM explanations for leads from a scoped operational run. | optional operational review support |
| `scripts/ml/run_llm_explainability.py` | Run dedicated LLM explanation prompt on selected evaluation leads. | current explainability evaluation |
| `scripts/ml/build_llm_explainability_leads.py` | Build explanation fields from existing LLM triage outputs. | evaluation experiment, not preferred for production |
| `scripts/ml/train_baseline_classifier.py` | Older baseline classifier workflow. | legacy candidate |

## Legacy scripts

| Script | Role | Status |
|---|---|---|
| `scripts/legacy/generate_baseline_leads.py` | Historical MVP baseline lead generation from `artifacts/scored_annotation_pool.jsonl`. | legacy reproduction helper. Optionally uses old baseline classifier predictions if present. Not part of scoped operational inference. |

## Data and result boundaries

| Path | Meaning | Git policy |
|---|---|---|
| `data/annotation/labeled/` | Curated labeled datasets and quality reports. | tracked when canonical |
| `data/annotation/evaluation/` | Frozen evaluation datasets and dataset reports. | tracked |
| `results/evaluation/` | Generated evaluation results, comparisons, reports, and LLM outputs. | tracked when report relevant |
| `data/models/` | Reproducible operational model artifacts. | tracked when small and current |
| `data/reference/` | Stable reference files. | tracked when deterministic and small |
| `artifacts/` | Generated operational outputs and local run artifacts. | ignored |
| `data/crawling/` | Raw crawled HTML. | ignored |
| `data/reference/geoadmin_search_cache.jsonl` | Runtime cache for GeoAdmin search. | ignored |

## Refactor candidates

The following scripts still contain logic that may later be moved into reusable modules or thinner wrappers.

| Script | Reason |
|---|---|
| `scripts/evaluation/evaluate_aligned_method_comparison.py` | Contains reusable comparison logic and TF IDF evaluation handling. |
| `scripts/evaluation/evaluate_hybrid_lead_selection.py` | Contains hybrid selection logic that informs operational candidate selection. |
| `scripts/evaluation/evaluate_scoring_against_annotations.py` | Older evaluation path based on global scored annotation pool. |
| `scripts/ml/train_baseline_classifier.py` | Superseded by `evaluate_classical_text_classifier.py` for current evaluation. |

## Operational boundary

The scoped operational pipeline is the supported runtime path.

Historical reproduction scripts remain available for auditability, but they may use fixed global paths and should not be treated as production runners.

Evaluation scripts may write to `results/evaluation/`.

Operational runs must write to `artifacts/runs/<run_id>/` and must not overwrite frozen datasets under `data/annotation/evaluation/`.
