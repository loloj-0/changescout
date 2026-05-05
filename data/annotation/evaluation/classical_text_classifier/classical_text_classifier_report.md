# Classical Text Classifier Evaluation

## Method

This evaluation uses a TF IDF plus Logistic Regression classifier.
The frozen train and test splits from Issue 15 are used.
The model is evaluated on the same strict binary and actionable binary datasets as the score baseline.

## Test metrics

### strict_binary

* Records: `53`
* Positives: `25`
* Negatives: `28`
* TP: `23`
* FP: `4`
* TN: `24`
* FN: `2`
* Precision: `0.852`
* Recall: `0.920`
* F1: `0.885`
* Accuracy: `0.887`

### actionable_binary

* Records: `70`
* Positives: `42`
* Negatives: `28`
* TP: `39`
* FP: `9`
* TN: `19`
* FN: `3`
* Precision: `0.812`
* Recall: `0.929`
* F1: `0.867`
* Accuracy: `0.829`

## Comparison with score baseline

### strict_binary

* Classifier F1: `0.885`
* Score baseline F1: `0.809`
* Classifier recall: `0.920`
* Score baseline recall: `0.760`
* Classifier precision: `0.852`
* Score baseline precision: `0.864`

### actionable_binary

* Classifier F1: `0.867`
* Score baseline F1: `0.822`
* Classifier recall: `0.929`
* Score baseline recall: `0.881`
* Classifier precision: `0.812`
* Score baseline precision: `0.771`

## Interpretation

This classifier is a learned non LLM baseline.
It tests whether a simple supervised text model improves over deterministic score based prioritization.
For the ChangeScout workflow, recall and lead usefulness are more important than accuracy alone.
