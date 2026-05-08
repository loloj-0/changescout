# Generated LLM Explainability Evaluation

## Scope

This report evaluates a dedicated explanation prompt for already selected ChangeScout leads.

The explanation model does not select or remove leads.

It generates evidence fields for human review.

## Run

* Model: `Qwen/Qwen2.5-7B-Instruct`
* Mode: `score_or_tfidf`
* Top N: `50`
* Records: `50`
* Parse success rate: `1.000`

## Evidence type counts

| Evidence type | Count |
|---|---:|
| confirmed_geometry | 22 |
| no_geometry_evidence | 14 |
| plausible_review_signal | 14 |

## Audit metrics

* Evidence snippets found in source: `45`
* Missing evidence snippets: `0`
* Requires manual explanation check: `19`

## Interpretation

The dedicated explanation prompt should be judged by auditability, not by classification accuracy.

A useful explanation must provide a source grounded evidence snippet and distinguish confirmed geometry from plausible review signals.

Any explanation with missing evidence, unsupported evidence, or no geometry evidence remains marked for manual checking.

## Output files

* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated.jsonl`
* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated.csv`
* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated_report.json`
* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated_report.md`
