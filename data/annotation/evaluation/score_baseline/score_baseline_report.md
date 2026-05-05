# Score Baseline Evaluation

## Method

The existing thematic score is evaluated as a threshold based classifier.
Thresholds are explored on the train split.
The best threshold is selected by train F1, with recall and precision as tie breakers.
Final selected threshold metrics are reported on the test split.

## Selected thresholds

* strict_binary: `0.25`
* actionable_binary: `0.05`

## Test metrics at selected thresholds

### strict_binary

* Threshold: `0.25`
* Records: `53`
* Positives: `25`
* Negatives: `28`
* TP: `19`
* FP: `3`
* TN: `25`
* FN: `6`
* Precision: `0.864`
* Recall: `0.760`
* F1: `0.809`
* Accuracy: `0.830`

### actionable_binary

* Threshold: `0.05`
* Records: `70`
* Positives: `42`
* Negatives: `28`
* TP: `37`
* FP: `11`
* TN: `17`
* FN: `5`
* Precision: `0.771`
* Recall: `0.881`
* F1: `0.822`
* Accuracy: `0.771`
