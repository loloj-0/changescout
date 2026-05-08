# LLM Explainability Output Evaluation

## Scope

This report evaluates explanation fields for selected ChangeScout leads.

The selected leads come from the hybrid lead selection workflow.

The LLM explanation is used for review support only.

It is not used as a hard exclusion signal and does not change candidate selection.

## Input selection

* Mode: `score_or_tfidf`
* Top N: `50`
* Records: `50`

## Evidence type counts

| Evidence type | Count |
|---|---:|
| confirmed_geometry | 18 |
| no_geometry_evidence | 24 |
| plausible_review_signal | 8 |

## LLM triage counts

| LLM triage class | Count |
|---|---:|
| confirmed_relevant | 18 |
| needs_review | 8 |
| not_relevant | 24 |

## Audit flags

* Missing evidence snippets: `1`
* LLM versus gold disagreement: `21`
* LLM predicted not_relevant for selected lead: `24`
* Requires manual explanation check: `32`

## Interpretation

The explainability output makes selected leads easier to inspect without changing the high recall selection logic.

The audit flags identify leads where the explanation should be checked manually before it is trusted.

In particular, LLM not_relevant predictions for selected leads must not remove the lead.

They only signal that the generated explanation may be weak or that the lead requires closer manual review.

## Output files

* `data/annotation/evaluation/llm_explainability/llm_explainability_leads.csv`
* `data/annotation/evaluation/llm_explainability/llm_explainability_leads.jsonl`
* `data/annotation/evaluation/llm_explainability/llm_explainability_report.json`
* `data/annotation/evaluation/llm_explainability/llm_explainability_report.md`
