# Evaluation Report Package

## Purpose

This package consolidates the current ChangeScout evaluation artifacts into report ready tables and interpretation notes.

It does not run new models.

It reads stored evaluation artifacts and rewrites a reproducible result package.

## Dataset summary

| dataset | records | train_records | test_records | train_confirmed_relevant | train_needs_review | train_not_relevant | test_confirmed_relevant | test_needs_review | test_not_relevant | all_confirmed_relevant | all_needs_review | all_not_relevant |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| strict_binary | 264 | 211 | 53 | 99 | 0 | 112 | 25 | 0 | 28 | 124 | 0 | 140 |
| actionable_binary | 348 | 278 | 70 | 103 | 63 | 112 | 21 | 21 | 28 | 124 | 84 | 140 |
| triage_3class | 348 | 278 | 70 | 99 | 67 | 112 | 25 | 17 | 28 | 124 | 84 | 140 |

## Aligned method comparison

All methods in this table are evaluated on the same frozen triage test records.

| task | method | method_type | records | positives | negatives | precision | recall | f1 | accuracy | tp | fp | tn | fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| actionable_binary | Qwen2.5 14B hierarchical | local_llm | 70 | 42 | 28 | 0.969 | 0.738 | 0.838 | 0.829 | 31 | 1 | 27 | 11 |
| actionable_binary | TF IDF Logistic Regression | classical_ml | 70 | 42 | 28 | 0.771 | 0.881 | 0.822 | 0.771 | 37 | 11 | 17 | 5 |
| actionable_binary | Qwen2.5 14B direct | local_llm | 70 | 42 | 28 | 0.938 | 0.714 | 0.811 | 0.800 | 30 | 2 | 26 | 12 |
| actionable_binary | thematic_score | deterministic_score | 70 | 42 | 28 | 0.750 | 0.857 | 0.800 | 0.743 | 36 | 12 | 16 | 6 |
| actionable_binary | Qwen2.5 7B direct | local_llm | 70 | 42 | 28 | 1.000 | 0.619 | 0.765 | 0.771 | 26 | 0 | 28 | 16 |
| actionable_binary | Qwen2.5 7B hierarchical | local_llm | 70 | 42 | 28 | 1.000 | 0.548 | 0.708 | 0.729 | 23 | 0 | 28 | 19 |
| actionable_binary | Llama 3.1 8B hierarchical | local_llm | 70 | 42 | 28 | 0.923 | 0.571 | 0.706 | 0.714 | 24 | 2 | 26 | 18 |
| strict_binary | thematic_score | deterministic_score | 53 | 25 | 28 | 0.957 | 0.880 | 0.917 | 0.925 | 22 | 1 | 27 | 3 |
| strict_binary | Qwen2.5 7B hierarchical | local_llm | 53 | 25 | 28 | 1.000 | 0.640 | 0.780 | 0.830 | 16 | 0 | 28 | 9 |
| strict_binary | TF IDF Logistic Regression | classical_ml | 53 | 25 | 28 | 0.688 | 0.880 | 0.772 | 0.755 | 22 | 10 | 18 | 3 |
| strict_binary | Qwen2.5 7B direct | local_llm | 53 | 25 | 28 | 1.000 | 0.600 | 0.750 | 0.811 | 15 | 0 | 28 | 10 |
| strict_binary | Llama 3.1 8B hierarchical | local_llm | 53 | 25 | 28 | 0.929 | 0.520 | 0.667 | 0.755 | 13 | 1 | 27 | 12 |
| strict_binary | Qwen2.5 14B hierarchical | local_llm | 53 | 25 | 28 | 1.000 | 0.120 | 0.214 | 0.585 | 3 | 0 | 28 | 22 |
| strict_binary | Qwen2.5 14B direct | local_llm | 53 | 25 | 28 | 1.000 | 0.120 | 0.214 | 0.585 | 3 | 0 | 28 | 22 |

## Strict binary comparison

Strict binary excludes needs_review cases and evaluates confirmed relevance only.

| task | method | method_type | records | positives | negatives | precision | recall | f1 | accuracy | tp | fp | tn | fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| strict_binary | thematic_score | deterministic_score | 53 | 25 | 28 | 0.957 | 0.880 | 0.917 | 0.925 | 22 | 1 | 27 | 3 |
| strict_binary | Qwen2.5 7B hierarchical | local_llm | 53 | 25 | 28 | 1.000 | 0.640 | 0.780 | 0.830 | 16 | 0 | 28 | 9 |
| strict_binary | TF IDF Logistic Regression | classical_ml | 53 | 25 | 28 | 0.688 | 0.880 | 0.772 | 0.755 | 22 | 10 | 18 | 3 |
| strict_binary | Qwen2.5 7B direct | local_llm | 53 | 25 | 28 | 1.000 | 0.600 | 0.750 | 0.811 | 15 | 0 | 28 | 10 |
| strict_binary | Llama 3.1 8B hierarchical | local_llm | 53 | 25 | 28 | 0.929 | 0.520 | 0.667 | 0.755 | 13 | 1 | 27 | 12 |
| strict_binary | Qwen2.5 14B hierarchical | local_llm | 53 | 25 | 28 | 1.000 | 0.120 | 0.214 | 0.585 | 3 | 0 | 28 | 22 |
| strict_binary | Qwen2.5 14B direct | local_llm | 53 | 25 | 28 | 1.000 | 0.120 | 0.214 | 0.585 | 3 | 0 | 28 | 22 |

## Actionable binary comparison

Actionable binary maps confirmed_relevant and needs_review to positive.

| task | method | method_type | records | positives | negatives | precision | recall | f1 | accuracy | tp | fp | tn | fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| actionable_binary | Qwen2.5 14B hierarchical | local_llm | 70 | 42 | 28 | 0.969 | 0.738 | 0.838 | 0.829 | 31 | 1 | 27 | 11 |
| actionable_binary | TF IDF Logistic Regression | classical_ml | 70 | 42 | 28 | 0.771 | 0.881 | 0.822 | 0.771 | 37 | 11 | 17 | 5 |
| actionable_binary | Qwen2.5 14B direct | local_llm | 70 | 42 | 28 | 0.938 | 0.714 | 0.811 | 0.800 | 30 | 2 | 26 | 12 |
| actionable_binary | thematic_score | deterministic_score | 70 | 42 | 28 | 0.750 | 0.857 | 0.800 | 0.743 | 36 | 12 | 16 | 6 |
| actionable_binary | Qwen2.5 7B direct | local_llm | 70 | 42 | 28 | 1.000 | 0.619 | 0.765 | 0.771 | 26 | 0 | 28 | 16 |
| actionable_binary | Qwen2.5 7B hierarchical | local_llm | 70 | 42 | 28 | 1.000 | 0.548 | 0.708 | 0.729 | 23 | 0 | 28 | 19 |
| actionable_binary | Llama 3.1 8B hierarchical | local_llm | 70 | 42 | 28 | 0.923 | 0.571 | 0.706 | 0.714 | 24 | 2 | 26 | 18 |

## Local LLM comparison

| model_id | prompt_variant | records | parse_success_rate | strict_precision | strict_recall | strict_f1 | actionable_precision | actionable_recall | actionable_f1 | triage_accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen2.5-14B-Instruct | direct | 70 | 1.000 | 1.000 | 0.120 | 0.214 | 0.938 | 0.714 | 0.811 | 0.529 |
| Qwen/Qwen2.5-14B-Instruct | hierarchical | 70 | 1.000 | 1.000 | 0.120 | 0.214 | 0.969 | 0.738 | 0.838 | 0.571 |
| Qwen/Qwen2.5-7B-Instruct | direct | 70 | 1.000 | 1.000 | 0.600 | 0.750 | 1.000 | 0.619 | 0.765 | 0.657 |
| Qwen/Qwen2.5-7B-Instruct | hierarchical | 70 | 1.000 | 1.000 | 0.640 | 0.780 | 1.000 | 0.548 | 0.708 | 0.671 |
| meta-llama/Llama-3.1-8B-Instruct | hierarchical | 70 | 1.000 | 0.929 | 0.520 | 0.667 | 0.923 | 0.571 | 0.706 | 0.586 |

## Hybrid lead selection summary

This table shows the preferred mode by review depth according to recall, precision, false negatives, and mode preference.

| n | mode | llm_run | records_total | selected_count | total_actionable | true_positives_at_n | false_positives_at_n | false_negatives_after_n | precision_at_n | recall_at_n | workload_fraction | workload_reduction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | tfidf_only | not_applicable | 70 | 10 | 42 | 10 | 0 | 32 | 1.000 | 0.238 | 0.143 | 0.857 |
| 20 | hybrid_recall_guard | qwen14b_hierarchical | 70 | 20 | 42 | 20 | 0 | 22 | 1.000 | 0.476 | 0.286 | 0.714 |
| 50 | score_or_tfidf | not_applicable | 70 | 50 | 42 | 39 | 11 | 3 | 0.780 | 0.929 | 0.714 | 0.286 |
| 70 | score_or_tfidf | not_applicable | 70 | 70 | 42 | 42 | 28 | 0 | 0.600 | 1.000 | 1.000 | 0.000 |

## LLM explainability summary

| metric | value |
| --- | --- |
| records | 50.000 |
| parse_success_rate | 1.000 |
| missing_evidence_snippet_count | 0.000 |
| evidence_snippet_found_in_source_count | 45.000 |
| requires_manual_explanation_check_count | 19.000 |
| evidence_type_confirmed_geometry | 22.000 |
| evidence_type_plausible_review_signal | 14.000 |
| evidence_type_no_geometry_evidence | 14.000 |

## Main interpretation

The deterministic thematic score remains the strongest strict confirmed relevance baseline on aligned records.

TF IDF Logistic Regression provides strong recall for actionable lead detection.

Qwen2.5 14B hierarchical achieves the highest actionable F1 among evaluated LLM runs, but it is weak for strict confirmed relevance because many confirmed cases are downgraded to needs_review.

Qwen2.5 14B direct is part of the direct versus hierarchical prompt comparison and does not improve over Qwen2.5 14B hierarchical.

Qwen2.5 7B variants are more production oriented and useful for evidence generation and review support.

The recommended lead selection strategy is score_or_tfidf candidate selection followed by LLM based explanation support.

LLM predictions are not hard exclusion signals.

## Output files in this package

* `dataset_summary.csv`
* `method_comparison_aligned.csv`
* `local_llm_comparison.csv`
* `hybrid_summary.csv`
* `explainability_summary.csv`
* `artifact_index.md`
* `limitations.md`
* `recommended_setup.md`

## Source reports for detailed inspection

Detailed confusion matrices, threshold selection reports, qualitative error analysis, and false negative examples are available in the source artifacts listed in `artifact_index.md`.

The package intentionally keeps derived summary tables separate from detailed source reports to avoid duplicating long outputs.

Key detailed reports:

* `data/annotation/evaluation/aligned_method_comparison/aligned_method_comparison.md`
* `data/annotation/evaluation/local_llm/comparison/local_llm_comparison.md`
* `data/annotation/evaluation/hybrid_lead_selection_comparison/hybrid_lead_selection_comparison.md`
* `data/annotation/evaluation/local_llm/error_analysis/llm_triage_error_analysis.md`
* `data/annotation/evaluation/hybrid_lead_selection_comparison/score_or_tfidf_top50_false_negatives.md`
* `data/annotation/evaluation/llm_explainability_generated/explainability_manual_review_notes.md`
