# Hybrid Lead Selection Evaluation

## Scope

This report evaluates lead selection strategies on the frozen aligned triage test split.

The target is actionable lead detection.

Positive actionable leads are confirmed_relevant and needs_review.

LLM predictions are used as enrichment and reprioritization signals.

LLM not_relevant predictions are not used as hard exclusion signals.

## Metrics

| Mode | N | Precision at N | Recall at N | False negatives after N | Workload reduction |
|---|---:|---:|---:|---:|---:|
| tfidf_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| llm_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| hybrid_weighted | 10 | 1.000 | 0.238 | 32 | 0.857 |
| hybrid_recall_guard | 10 | 1.000 | 0.238 | 32 | 0.857 |
| score_only | 10 | 0.900 | 0.214 | 33 | 0.857 |
| score_or_tfidf | 10 | 0.900 | 0.214 | 33 | 0.857 |
| llm_only | 20 | 1.000 | 0.476 | 22 | 0.714 |
| hybrid_weighted | 20 | 1.000 | 0.476 | 22 | 0.714 |
| hybrid_recall_guard | 20 | 1.000 | 0.476 | 22 | 0.714 |
| score_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| tfidf_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| score_or_tfidf | 20 | 0.900 | 0.429 | 24 | 0.714 |
| score_or_tfidf | 50 | 0.780 | 0.929 | 3 | 0.286 |
| hybrid_weighted | 50 | 0.780 | 0.929 | 3 | 0.286 |
| hybrid_recall_guard | 50 | 0.780 | 0.929 | 3 | 0.286 |
| score_only | 50 | 0.760 | 0.905 | 4 | 0.286 |
| tfidf_only | 50 | 0.740 | 0.881 | 5 | 0.286 |
| llm_only | 50 | 0.740 | 0.881 | 5 | 0.286 |
| score_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| tfidf_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| llm_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| score_or_tfidf | 70 | 0.600 | 1.000 | 0 | 0.000 |
| hybrid_weighted | 70 | 0.600 | 1.000 | 0 | 0.000 |
| hybrid_recall_guard | 70 | 0.600 | 1.000 | 0 | 0.000 |

## Interpretation

The useful hybrid strategy is the one that improves recall at practical review depth without relying on the LLM as a hard filter.

A high precision LLM signal can improve priority ordering and evidence quality.

However, because local LLM false negatives remain frequent, LLM not_relevant should only downgrade a lead and should not remove it when score or TF IDF signals are strong.

## Output files

* `data/annotation/evaluation/hybrid_lead_selection/hybrid_lead_selection_metrics.csv`
* `data/annotation/evaluation/hybrid_lead_selection/hybrid_leads.csv`
* `data/annotation/evaluation/hybrid_lead_selection/hybrid_lead_selection_report.md`
