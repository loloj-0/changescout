# Evaluation datasets

This directory contains frozen task specific evaluation datasets derived from the canonical labeled ChangeScout dataset.

## Source dataset

The source dataset is:

`data/annotation/labeled/annotation_dataset_expanded.csv`

It contains 348 manually reviewed records.

## Purpose

These files are not separate annotation sources.

They are derived evaluation views with fixed train and test splits.

They are tracked to make evaluation runs reproducible.

## Files

`strict_binary_dataset.csv`

Strict binary relevance task.

`confirmed_relevant` is positive.

`not_relevant` is negative.

`needs_review` is excluded.

`actionable_binary_dataset.csv`

Actionable lead task.

`confirmed_relevant` and `needs_review` are positive.

`not_relevant` is negative.

`triage_3class_dataset.csv`

Three class triage task.

Classes are `confirmed_relevant`, `needs_review`, and `not_relevant`.

`evaluation_dataset_report.md`

Human readable report describing input, splits, counts, and label mappings.

`evaluation_dataset_report.json`

Machine readable report describing input, splits, counts, and label mappings.

## Status

These datasets are frozen evaluation inputs.

They should only be regenerated deliberately from `annotation_dataset_expanded.csv` using:

`python scripts/evaluation/build_evaluation_datasets.py`
