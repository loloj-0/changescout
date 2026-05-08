# Labeled annotation dataset

This directory contains the canonical manually labeled ChangeScout dataset.

## Canonical dataset

The canonical labeled dataset is:

`annotation_dataset_expanded.csv`

It contains 348 manually reviewed records from official canton level web sources.

The dataset combines records from multiple cantons and source types into one frozen annotation corpus.

## Machine readable copy

`annotation_dataset_expanded.jsonl`

This file contains the same final labeled records in JSONL format.

## Reports

`annotation_dataset_expanded_report.json`

Build report for the final expanded dataset.

`annotation_dataset_quality_report.md`

Human readable quality report for the final dataset.

`annotation_dataset_quality_report.json`

Machine readable quality report for the final dataset.

## Status

The reviewed Excel files used during manual annotation were intermediate working artifacts.

They are not the canonical dataset and are not used as downstream model inputs.

Downstream evaluation and model training should use the frozen datasets derived from `annotation_dataset_expanded.csv`.
