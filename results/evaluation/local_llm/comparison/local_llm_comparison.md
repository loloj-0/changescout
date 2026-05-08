# Local LLM Comparison

## Summary

| Model | Prompt | Parse | Strict P | Strict R | Strict F1 | Actionable P | Actionable R | Actionable F1 | Triage Acc |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | hierarchical | 1.000 | 1.000 | 0.120 | 0.214 | 0.969 | 0.738 | 0.838 | 0.571 |
| Qwen/Qwen2.5-14B-Instruct | direct | 1.000 | 1.000 | 0.120 | 0.214 | 0.938 | 0.714 | 0.811 | 0.529 |
| Qwen/Qwen2.5-7B-Instruct | direct | 1.000 | 1.000 | 0.600 | 0.750 | 1.000 | 0.619 | 0.765 | 0.657 |
| Qwen/Qwen2.5-7B-Instruct | hierarchical | 1.000 | 1.000 | 0.640 | 0.780 | 1.000 | 0.548 | 0.708 | 0.671 |
| meta-llama/Llama-3.1-8B-Instruct | hierarchical | 1.000 | 0.929 | 0.520 | 0.667 | 0.923 | 0.571 | 0.706 | 0.586 |

## Interpretation

All local LLMs were evaluated on the frozen triage test split.
Strict binary and actionable binary metrics are derived from the same triage predictions.
For ChangeScout, actionable recall and actionable F1 are more relevant than global accuracy because the workflow is lead prioritization with human review.
