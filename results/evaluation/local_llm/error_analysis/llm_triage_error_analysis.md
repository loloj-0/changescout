# LLM Triage Error Analysis

## Error summary

| Run | Error type | Count |
|---|---|---:|
| llama31_8b_hierarchical | needs_review_to_not_relevant | 11 |
| llama31_8b_hierarchical | confirmed_relevant_to_not_relevant | 7 |
| llama31_8b_hierarchical | confirmed_relevant_to_needs_review | 5 |
| llama31_8b_hierarchical | needs_review_to_confirmed_relevant | 4 |
| llama31_8b_hierarchical | not_relevant_to_confirmed_relevant | 1 |
| llama31_8b_hierarchical | not_relevant_to_needs_review | 1 |
| qwen14b_hierarchical | confirmed_relevant_to_needs_review | 18 |
| qwen14b_hierarchical | needs_review_to_not_relevant | 7 |
| qwen14b_hierarchical | confirmed_relevant_to_not_relevant | 4 |
| qwen14b_hierarchical | not_relevant_to_needs_review | 1 |
| qwen7b_direct | needs_review_to_not_relevant | 11 |
| qwen7b_direct | confirmed_relevant_to_needs_review | 5 |
| qwen7b_direct | confirmed_relevant_to_not_relevant | 5 |
| qwen7b_direct | needs_review_to_confirmed_relevant | 3 |
| qwen7b_hierarchical | needs_review_to_not_relevant | 13 |
| qwen7b_hierarchical | confirmed_relevant_to_not_relevant | 6 |
| qwen7b_hierarchical | confirmed_relevant_to_needs_review | 3 |
| qwen7b_hierarchical | needs_review_to_confirmed_relevant | 1 |

## Interpretation

The dominant error patterns differ by model.

Qwen2.5 7B and Llama 3.1 8B are conservative and often map needs_review to not_relevant.

Qwen2.5 14B is more sensitive for actionable leads, but often maps confirmed_relevant to needs_review.

This means local zero shot LLMs are useful for structured evidence and precision oriented review support, but are not stable enough as standalone three class triage classifiers.

For ChangeScout, the most robust design remains a hybrid workflow: high recall candidate selection by score or TF IDF, followed by LLM based evidence generation and optional precision support.

## Practical implication

LLM outputs should not be used as hard exclusion signals.

An LLM prediction of not_relevant can downgrade priority, but should not remove a candidate if the score or TF IDF classifier indicates actionable relevance.
