# Local LLM Triage Evaluation

* Model: `meta-llama/Llama-3.1-8B-Instruct`
* Prompt variant: `hierarchical`
* Records: `70`
* Parse success rate: `1.000`

## Binary metrics

### strict_binary

* Records: `53`
* TP: `13`
* FP: `1`
* TN: `27`
* FN: `12`
* Precision: `0.929`
* Recall: `0.520`
* F1: `0.667`
* Accuracy: `0.755`

### actionable_binary

* Records: `70`
* TP: `24`
* FP: `2`
* TN: `26`
* FN: `18`
* Precision: `0.923`
* Recall: `0.571`
* F1: `0.706`
* Accuracy: `0.714`

## Three class triage

* Accuracy: `0.586`

Labels:

* `confirmed_relevant`
* `needs_review`
* `not_relevant`
* `invalid`

Confusion matrix rows are gold labels, columns are predicted labels.

```text
[13, 5, 7, 0]
[4, 2, 11, 0]
[1, 1, 26, 0]
[0, 0, 0, 0]
```

## Baseline comparison

### score_baseline

* strict_binary: precision `0.864`, recall `0.760`, F1 `0.809`
* actionable_binary: precision `0.771`, recall `0.881`, F1 `0.822`

### classical_text_classifier

* strict_binary: precision `0.852`, recall `0.920`, F1 `0.885`
* actionable_binary: precision `0.812`, recall `0.929`, F1 `0.867`
