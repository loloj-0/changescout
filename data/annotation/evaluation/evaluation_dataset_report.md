# Evaluation Dataset Report

## Input

* Input path: `data/annotation/labeled/annotation_dataset_expanded.csv`
* Input rows: `348`
* Test size: `0.2`
* Random state: `42`

## Outputs

### strict_binary

* Path: `data/annotation/evaluation/strict_binary_dataset.csv`
* Rows: `264`
* Target column: `target_strict_relevant`
* Split column: `split`

Class counts:

* 0: `140`
* 1: `124`

Split counts:

* train: `211`
* test: `53`

### actionable_binary

* Path: `data/annotation/evaluation/actionable_binary_dataset.csv`
* Rows: `348`
* Target column: `target_actionable`
* Split column: `split`

Class counts:

* 1: `208`
* 0: `140`

Split counts:

* train: `278`
* test: `70`

### triage_3class

* Path: `data/annotation/evaluation/triage_3class_dataset.csv`
* Rows: `348`
* Target column: `target_triage_class`
* Split column: `split`

Class counts:

* not_relevant: `140`
* confirmed_relevant: `124`
* needs_review: `84`

Split counts:

* train: `278`
* test: `70`

## Label mapping

### strict_binary

* confirmed_relevant -> 1
* not_relevant -> 0
* needs_review -> excluded

### actionable_binary

* confirmed_relevant -> 1
* needs_review -> 1
* not_relevant -> 0

### triage_3class

* confirmed_relevant
* needs_review
* not_relevant
