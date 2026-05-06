# Model Artifacts

ChangeScout operational runs may use learned model artifacts.

Model artifacts must be reproducible and auditable.

## Current artifact

The current learned operational artifact is:

`tfidf_actionable`

It is a TF IDF plus Logistic Regression classifier for actionable lead probability.

The target is:

* `confirmed_relevant` and `needs_review` as positive
* `not_relevant` as negative

## Default location

`data/models/tfidf_actionable/<model_version>/`

Expected files:

* `model.joblib`
* `metadata.json`
* `test_predictions.csv`

## Required metadata

Each artifact must include:

* model version
* model type
* target definition
* positive classes
* creation timestamp
* training dataset path
* training dataset SHA256 hash
* train and test split names
* train and test record counts
* model parameters
* evaluation metrics
* threshold

## Operational use

Operational inference must load the artifact explicitly.

It must not retrain inside an operational run.

It writes TF IDF fields to scoped operational outputs.

Current operational output:

`artifacts/runs/<run_id>/scored_with_tfidf.jsonl`

Current operational report:

`artifacts/runs/<run_id>/reports/tfidf_inference_report.json`

## Boundary

TF IDF probability is a learned review signal.

It is not a confirmed TLM update.

Hybrid candidate selection is implemented separately.

LLM outputs remain review support and are not hard exclusion signals.
