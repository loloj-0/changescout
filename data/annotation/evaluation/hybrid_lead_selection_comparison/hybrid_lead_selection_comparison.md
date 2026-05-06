# Hybrid Lead Selection Comparison

## Scope

This report compares hybrid lead selection results across local LLM variants.

All runs use the same frozen aligned triage test split.

The target is actionable lead detection.

Positive actionable leads are confirmed_relevant and needs_review.

LLM predictions are used as enrichment and reprioritization signals, not as hard exclusion signals.

## Metrics

| LLM run | Mode | N | Precision at N | Recall at N | False negatives after N | Workload reduction |
|---|---|---:|---:|---:|---:|---:|
| qwen14b_direct | tfidf_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_direct | llm_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_direct | hybrid_weighted | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_direct | hybrid_recall_guard | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_hierarchical | tfidf_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_hierarchical | llm_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_hierarchical | hybrid_weighted | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_hierarchical | hybrid_recall_guard | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_direct | tfidf_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_direct | llm_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_direct | hybrid_weighted | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_direct | hybrid_recall_guard | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_hierarchical | tfidf_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_hierarchical | llm_only | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_hierarchical | hybrid_weighted | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen7b_hierarchical | hybrid_recall_guard | 10 | 1.000 | 0.238 | 32 | 0.857 |
| qwen14b_direct | score_only | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen14b_direct | score_or_tfidf | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen14b_hierarchical | score_only | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen14b_hierarchical | score_or_tfidf | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen7b_direct | score_only | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen7b_direct | score_or_tfidf | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen7b_hierarchical | score_only | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen7b_hierarchical | score_or_tfidf | 10 | 0.900 | 0.214 | 33 | 0.857 |
| qwen14b_direct | llm_only | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen14b_direct | hybrid_weighted | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen14b_direct | hybrid_recall_guard | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen14b_hierarchical | llm_only | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen14b_hierarchical | hybrid_weighted | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen14b_hierarchical | hybrid_recall_guard | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen7b_direct | llm_only | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen7b_direct | hybrid_weighted | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen7b_direct | hybrid_recall_guard | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen7b_hierarchical | llm_only | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen7b_hierarchical | hybrid_weighted | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen7b_hierarchical | hybrid_recall_guard | 20 | 1.000 | 0.476 | 22 | 0.714 |
| qwen14b_direct | score_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen14b_direct | tfidf_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen14b_hierarchical | score_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen14b_hierarchical | tfidf_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen7b_direct | score_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen7b_direct | tfidf_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen7b_hierarchical | score_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen7b_hierarchical | tfidf_only | 20 | 0.950 | 0.452 | 23 | 0.714 |
| qwen14b_direct | score_or_tfidf | 20 | 0.900 | 0.429 | 24 | 0.714 |
| qwen14b_hierarchical | score_or_tfidf | 20 | 0.900 | 0.429 | 24 | 0.714 |
| qwen7b_direct | score_or_tfidf | 20 | 0.900 | 0.429 | 24 | 0.714 |
| qwen7b_hierarchical | score_or_tfidf | 20 | 0.900 | 0.429 | 24 | 0.714 |
| qwen14b_direct | score_or_tfidf | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen14b_direct | hybrid_weighted | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen14b_direct | hybrid_recall_guard | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen14b_hierarchical | score_or_tfidf | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen14b_hierarchical | hybrid_weighted | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen14b_hierarchical | hybrid_recall_guard | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen7b_direct | score_or_tfidf | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen7b_direct | hybrid_weighted | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen7b_direct | hybrid_recall_guard | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen7b_hierarchical | score_or_tfidf | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen7b_hierarchical | hybrid_weighted | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen7b_hierarchical | hybrid_recall_guard | 50 | 0.780 | 0.929 | 3 | 0.286 |
| qwen14b_direct | score_only | 50 | 0.760 | 0.905 | 4 | 0.286 |
| qwen14b_hierarchical | score_only | 50 | 0.760 | 0.905 | 4 | 0.286 |
| qwen7b_direct | score_only | 50 | 0.760 | 0.905 | 4 | 0.286 |
| qwen7b_hierarchical | score_only | 50 | 0.760 | 0.905 | 4 | 0.286 |
| qwen14b_direct | tfidf_only | 50 | 0.740 | 0.881 | 5 | 0.286 |
| qwen14b_hierarchical | tfidf_only | 50 | 0.740 | 0.881 | 5 | 0.286 |
| qwen14b_hierarchical | llm_only | 50 | 0.740 | 0.881 | 5 | 0.286 |
| qwen7b_direct | tfidf_only | 50 | 0.740 | 0.881 | 5 | 0.286 |
| qwen7b_hierarchical | tfidf_only | 50 | 0.740 | 0.881 | 5 | 0.286 |
| qwen14b_direct | llm_only | 50 | 0.700 | 0.833 | 7 | 0.286 |
| qwen7b_direct | llm_only | 50 | 0.660 | 0.786 | 9 | 0.286 |
| qwen7b_hierarchical | llm_only | 50 | 0.640 | 0.762 | 10 | 0.286 |
| qwen14b_direct | score_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_direct | tfidf_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_direct | llm_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_direct | score_or_tfidf | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_direct | hybrid_weighted | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_direct | hybrid_recall_guard | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_hierarchical | score_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_hierarchical | tfidf_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_hierarchical | llm_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_hierarchical | score_or_tfidf | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_hierarchical | hybrid_weighted | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen14b_hierarchical | hybrid_recall_guard | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_direct | score_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_direct | tfidf_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_direct | llm_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_direct | score_or_tfidf | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_direct | hybrid_weighted | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_direct | hybrid_recall_guard | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_hierarchical | score_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_hierarchical | tfidf_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_hierarchical | llm_only | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_hierarchical | score_or_tfidf | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_hierarchical | hybrid_weighted | 70 | 0.600 | 1.000 | 0 | 0.000 |
| qwen7b_hierarchical | hybrid_recall_guard | 70 | 0.600 | 1.000 | 0 | 0.000 |

## Best modes by review depth

| N | Best mode | LLM dependency | Recall | Precision | False negatives |
|---:|---|---|---:|---:|---:|
| 10 | tfidf_only | not_applicable | 0.238 | 1.000 | 32 |
| 20 | hybrid_recall_guard | qwen14b_direct, qwen14b_hierarchical, qwen7b_direct, qwen7b_hierarchical | 0.476 | 1.000 | 22 |
| 50 | score_or_tfidf | not_applicable | 0.929 | 0.780 | 3 |
| 70 | score_or_tfidf | not_applicable | 1.000 | 0.600 | 0 |

## Findings

* At top 10, TF IDF, LLM only, and hybrid variants reach perfect precision and identical recall across the evaluated LLM variants.
* At top 20, LLM only and hybrid variants reach perfect precision and the highest recall.
* At top 50, score_or_tfidf and hybrid variants recover the most actionable leads.
* Qwen2.5 14B hierarchical is the strongest LLM signal for actionable F1, but it is not the preferred production default because it is computationally heavier and required CPU offload in the current environment.
* Qwen2.5 7B variants are more production oriented and still useful for shallow priority ranking and evidence generation.
* The high recall gain at broader review depth mainly comes from combining thematic_score and TF IDF probability.
* LLM not_relevant predictions should not be used as hard exclusion signals.

## Recommended hybrid strategy

Use score_or_tfidf as the high recall candidate selection layer.

Use a production feasible local LLM such as Qwen2.5 7B for evidence generation, triage notes, and optional priority support.

Use Qwen2.5 14B as an upper bound evaluation signal, not as the default production model.
