# Hybrid Lead Selection False Negatives

## Scope

This report lists actionable records missed by the recommended high recall strategy at top 50.

Recommended strategy: score_or_tfidf.

Review depth: 50 of 70 records.

## False negatives

| Annotation ID | Triage class | Title | Source | Score | TF IDF probability | LLM class |
|---|---|---|---|---:|---:|---|
| ann_0010 | confirmed_relevant | Die Mobilitätsdrehscheibe Bahnhof Solothurn Süd nimmt Fahrt auf - Kanton Solothurn | so_media_2025_februar | 0.260 | 0.410 | not_relevant |
| ann_0024 | needs_review | Regierungsratssitzung vom 28. Oktober 2025 - Kanton Solothurn | so_media_2025_oktober | 0.121 | 0.220 | not_relevant |
| ann_0047 | needs_review | Regierungsratssitzung vom 29. Oktober 2024 - Kanton Solothurn | so_media_2024_oktober | 0.000 | 0.195 | not_relevant |

## Interpretation

The remaining false negatives are mainly broad or aggregated government communication pages.

Their relevant TLM signal is not prominent enough for the current score, TF IDF, or LLM signals.

This supports keeping the hybrid workflow human in the loop and treating LLM not_relevant as a downgrade signal rather than a hard exclusion.
