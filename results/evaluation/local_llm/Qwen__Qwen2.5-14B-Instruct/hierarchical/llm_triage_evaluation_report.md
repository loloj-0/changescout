# Local LLM Triage Evaluation

* Model: `Qwen/Qwen2.5-14B-Instruct`
* Prompt variant: `hierarchical`
* Records: `70`
* Parse success rate: `1.000`

## Binary metrics

### strict_binary

* Records: `53`
* TP: `3`
* FP: `0`
* TN: `28`
* FN: `22`
* Precision: `1.000`
* Recall: `0.120`
* F1: `0.214`
* Accuracy: `0.585`

### actionable_binary

* Records: `70`
* TP: `31`
* FP: `1`
* TN: `27`
* FN: `11`
* Precision: `0.969`
* Recall: `0.738`
* F1: `0.838`
* Accuracy: `0.829`

## Three class triage

* Accuracy: `0.571`

Labels:

* `confirmed_relevant`
* `needs_review`
* `not_relevant`
* `invalid`

Confusion matrix rows are gold labels, columns are predicted labels.

```text
[3, 18, 4, 0]
[0, 10, 7, 0]
[0, 1, 27, 0]
[0, 0, 0, 0]
```

## Baseline comparison

### score_baseline

* strict_binary: precision `0.864`, recall `0.760`, F1 `0.809`
* actionable_binary: precision `0.771`, recall `0.881`, F1 `0.822`

### classical_text_classifier

* strict_binary: precision `0.852`, recall `0.920`, F1 `0.885`
* actionable_binary: precision `0.812`, recall `0.929`, F1 `0.867`
