# Aligned Method Comparison

All methods are evaluated on the same frozen triage test split.

Strict binary excludes needs_review cases.

Actionable binary maps confirmed_relevant and needs_review to positive.

| Task | Method | Type | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| actionable_binary | Qwen2.5 14B hierarchical | local_llm | 0.969 | 0.738 | 0.838 | 0.829 | 31 | 1 | 27 | 11 |
| actionable_binary | TF IDF Logistic Regression | classical_ml | 0.771 | 0.881 | 0.822 | 0.771 | 37 | 11 | 17 | 5 |
| actionable_binary | thematic_score | deterministic_score | 0.750 | 0.857 | 0.800 | 0.743 | 36 | 12 | 16 | 6 |
| actionable_binary | Qwen2.5 7B direct | local_llm | 1.000 | 0.619 | 0.765 | 0.771 | 26 | 0 | 28 | 16 |
| actionable_binary | Qwen2.5 7B hierarchical | local_llm | 1.000 | 0.548 | 0.708 | 0.729 | 23 | 0 | 28 | 19 |
| actionable_binary | Llama 3.1 8B hierarchical | local_llm | 0.923 | 0.571 | 0.706 | 0.714 | 24 | 2 | 26 | 18 |
| strict_binary | thematic_score | deterministic_score | 0.957 | 0.880 | 0.917 | 0.925 | 22 | 1 | 27 | 3 |
| strict_binary | Qwen2.5 7B hierarchical | local_llm | 1.000 | 0.640 | 0.780 | 0.830 | 16 | 0 | 28 | 9 |
| strict_binary | TF IDF Logistic Regression | classical_ml | 0.688 | 0.880 | 0.772 | 0.755 | 22 | 10 | 18 | 3 |
| strict_binary | Qwen2.5 7B direct | local_llm | 1.000 | 0.600 | 0.750 | 0.811 | 15 | 0 | 28 | 10 |
| strict_binary | Llama 3.1 8B hierarchical | local_llm | 0.929 | 0.520 | 0.667 | 0.755 | 13 | 1 | 27 | 12 |
| strict_binary | Qwen2.5 14B hierarchical | local_llm | 1.000 | 0.120 | 0.214 | 0.585 | 3 | 0 | 28 | 22 |

## Interpretation

This report removes the split alignment issue by evaluating all methods on the same triage test records.

The TF IDF classifier is trained on the corresponding triage train split for each binary target.

The score baseline threshold is selected on the corresponding triage train split.

Local LLM predictions are evaluated on the same triage test split without additional inference.
