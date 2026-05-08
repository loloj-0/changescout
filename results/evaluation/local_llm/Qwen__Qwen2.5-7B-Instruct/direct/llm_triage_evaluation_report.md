# Local LLM Triage Evaluation

* Model: `Qwen/Qwen2.5-7B-Instruct`
* Prompt variant: `direct`
* Records: `70`
* Parse success rate: `1.000`

## Binary metrics

### strict_binary

* Records: `53`
* TP: `15`
* FP: `0`
* TN: `28`
* FN: `10`
* Precision: `1.000`
* Recall: `0.600`
* F1: `0.750`
* Accuracy: `0.811`

### actionable_binary

* Records: `70`
* TP: `26`
* FP: `0`
* TN: `28`
* FN: `16`
* Precision: `1.000`
* Recall: `0.619`
* F1: `0.765`
* Accuracy: `0.771`

## Three class triage

* Accuracy: `0.657`

Labels:

* `confirmed_relevant`
* `needs_review`
* `not_relevant`
* `invalid`

Confusion matrix rows are gold labels, columns are predicted labels.

```text
[15, 5, 5, 0]
[3, 3, 11, 0]
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
