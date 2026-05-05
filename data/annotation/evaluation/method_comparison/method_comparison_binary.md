# ChangeScout Method Comparison

## Binary evaluation

| Dataset | Method | Type | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| actionable_binary | tfidf_logistic_regression | classical_ml | 0.812 | 0.929 | 0.867 | 0.829 | 39 | 9 | 19 | 3 |
| actionable_binary | Qwen/Qwen2.5-14B-Instruct [hierarchical] | local_llm | 0.969 | 0.738 | 0.838 | 0.829 | 31 | 1 | 27 | 11 |
| actionable_binary | thematic_score | deterministic_score | 0.771 | 0.881 | 0.822 | 0.771 | 37 | 11 | 17 | 5 |
| actionable_binary | Qwen/Qwen2.5-7B-Instruct [direct] | local_llm | 1.000 | 0.619 | 0.765 | 0.771 | 26 | 0 | 28 | 16 |
| actionable_binary | Qwen/Qwen2.5-7B-Instruct [hierarchical] | local_llm | 1.000 | 0.548 | 0.708 | 0.729 | 23 | 0 | 28 | 19 |
| actionable_binary | meta-llama/Llama-3.1-8B-Instruct [hierarchical] | local_llm | 0.923 | 0.571 | 0.706 | 0.714 | 24 | 2 | 26 | 18 |
| strict_binary | tfidf_logistic_regression | classical_ml | 0.852 | 0.920 | 0.885 | 0.887 | 23 | 4 | 24 | 2 |
| strict_binary | thematic_score | deterministic_score | 0.864 | 0.760 | 0.809 | 0.830 | 19 | 3 | 25 | 6 |
| strict_binary | Qwen/Qwen2.5-7B-Instruct [hierarchical] | local_llm | 1.000 | 0.640 | 0.780 | 0.830 | 16 | 0 | 28 | 9 |
| strict_binary | Qwen/Qwen2.5-7B-Instruct [direct] | local_llm | 1.000 | 0.600 | 0.750 | 0.811 | 15 | 0 | 28 | 10 |
| strict_binary | meta-llama/Llama-3.1-8B-Instruct [hierarchical] | local_llm | 0.929 | 0.520 | 0.667 | 0.755 | 13 | 1 | 27 | 12 |
| strict_binary | Qwen/Qwen2.5-14B-Instruct [hierarchical] | local_llm | 1.000 | 0.120 | 0.214 | 0.585 | 3 | 0 | 28 | 22 |

## Interpretation

The TF IDF Logistic Regression classifier is the strongest method on both strict binary relevance and actionable lead detection.
The local LLMs produce valid structured outputs and high precision, but their recall is lower than the deterministic score baseline and the classical classifier.
Qwen 14B improves actionable lead detection compared with smaller local LLMs, mainly by assigning many confirmed relevant cases to needs_review rather than not_relevant.
For ChangeScout, the most plausible role of local LLMs is not standalone lead discovery, but hybrid review support, precision filtering, and evidence generation.
