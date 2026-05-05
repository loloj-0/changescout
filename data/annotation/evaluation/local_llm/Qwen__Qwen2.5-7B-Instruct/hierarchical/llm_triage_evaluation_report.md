# Local LLM Triage Evaluation

* Model: `Qwen/Qwen2.5-7B-Instruct`
* Prompt variant: `hierarchical`
* Records: `70`
* Parse success rate: `1.000`

## Binary metrics

### strict_binary

* Records: `53`
* TP: `16`
* FP: `0`
* TN: `28`
* FN: `9`
* Precision: `1.000`
* Recall: `0.640`
* F1: `0.780`
* Accuracy: `0.830`

### actionable_binary

* Records: `70`
* TP: `23`
* FP: `0`
* TN: `28`
* FN: `19`
* Precision: `1.000`
* Recall: `0.548`
* F1: `0.708`
* Accuracy: `0.729`

## Three class triage

* Accuracy: `0.671`

Labels:

* `confirmed_relevant`
* `needs_review`
* `not_relevant`
* `invalid`

Confusion matrix rows are gold labels, columns are predicted labels.

```text
[16, 3, 6, 0]
[1, 3, 13, 0]
[0, 0, 28, 0]
[0, 0, 0, 0]
```

## Baseline comparison

### score_baseline

* strict_binary: precision `0.864`, recall `0.760`, F1 `0.809`
* actionable_binary: precision `0.771`, recall `0.881`, F1 `0.822`

### classical_text_classifier

* strict_binary: precision `0.852`, recall `0.920`, F1 `0.885`
* actionable_binary: precision `0.812`, recall `0.929`, F1 `0.867`
