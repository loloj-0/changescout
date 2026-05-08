# Recommended Setup

The recommended current setup is a human in the loop review workflow.

Candidate selection should use `score_or_tfidf`.

This combines deterministic thematic scoring and TF IDF actionable probability.

For the aligned triage test split, the top 50 `score_or_tfidf` review queue reached high actionable recall with limited workload.

The LLM should be used after candidate selection.

The recommended LLM role is evidence generation, explanation, triage notes, and optional priority support.

A production feasible model such as Qwen2.5 7B is preferred for this support layer.

Qwen2.5 14B is useful for comparison, but not required as default production model.

LLM predictions must not be used as hard exclusion signals.

The explanation layer should attach audit fields to each generated explanation.

Reviewers should treat the explanation as support, not as authoritative proof.
