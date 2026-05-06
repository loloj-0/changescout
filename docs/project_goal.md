# ChangeScout Project Goal

## Purpose

ChangeScout is a lead prioritization and review support system for potential TLM relevant changes.

The system monitors manually curated official canton level web sources, extracts relevant text, scores candidate documents, and produces prioritized review leads.

ChangeScout is not an automatic TLM update system.

ChangeScout is not intended to replace expert judgement.

The goal is to reduce manual search and screening effort by surfacing potentially relevant official sources earlier and in a reproducible order.

## Operational goal

The operational goal is to support a human in the loop review workflow.

The system should answer:

Which official sources should a reviewer inspect first because they may contain TLM relevant geometry changes?

The system should not answer as a final automated decision:

Should TLM be updated now?

A lead is therefore not a confirmed TLM change.

A lead is a prioritized review candidate.

## TLM relevance

A source is relevant for ChangeScout when it may indicate a persistent change that affects TLM road or path geometry.

Relevant examples include:

1. new roads or paths
2. changed alignments
3. new or changed junctions
4. new roundabouts
5. changed entries or exits
6. new bridges, tunnels, underpasses, or galleries with geometry effect
7. new physically separated pedestrian or cycling infrastructure
8. mapped road related geometries such as traffic islands

General construction activity alone is not enough.

Maintenance, resurfacing, temporary traffic management, markings, and administrative updates are not confirmed TLM relevance unless they imply a persistent geometry update.

## Review classes

The expanded annotation dataset uses three review classes.

| Class | Meaning |
|---|---|
| confirmed_relevant | The source text provides sufficient evidence for a persistent TLM geometry update. |
| needs_review | The source contains plausible TLM signals, but the evidence is insufficient for confirmed relevance. |
| not_relevant | The source does not contain a plausible TLM geometry update signal. |

These classes are derived from the annotation labels.

| tlm_relevant | review_required | triage_class |
|---|---|---|
| true | false | confirmed_relevant |
| false | true | needs_review |
| false | false | not_relevant |
| true | true | invalid |

The combination `tlm_relevant = true` and `review_required = true` is invalid.

## Evaluation goal

The main evaluation goal is not maximum classification accuracy.

The main evaluation goal is useful lead prioritization.

Important metrics are:

1. recall for actionable leads
2. precision at N
3. recall at N
4. false negative analysis
5. review workload reduction
6. quality of explanations for human review

Accuracy and F1 are still reported, but they are not sufficient to judge the system.

A false positive usually means additional review effort.

A false negative can mean that a relevant source is missed.

Therefore, recall and top ranked lead quality are central for the MVP.

## Baseline interpretation

The thematic score is a deterministic ranking signal.

It is useful for prioritizing sources, but it is not a final semantic relevance decision.

The score can overrate texts that contain many infrastructure terms without confirmed geometry changes.

The score can underrate texts where a real TLM relevant signal is described indirectly or late in the source.

The baseline is therefore evaluated as a lead prioritization mechanism.

## Current non LLM baseline results

Two non LLM baselines have been evaluated on the frozen test splits.

| Dataset | Method | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| strict_binary | thematic_score | 0.864 | 0.760 | 0.809 |
| strict_binary | TF IDF Logistic Regression | 0.852 | 0.920 | 0.885 |
| actionable_binary | thematic_score | 0.771 | 0.881 | 0.822 |
| actionable_binary | TF IDF Logistic Regression | 0.812 | 0.929 | 0.867 |

The deterministic score baseline already provides practical value as a review queue prioritization mechanism.

The TF IDF Logistic Regression baseline improves recall and F1 on both binary tasks.

This makes it the stronger non LLM baseline for subsequent LLM comparison.

The result also confirms that the project should be evaluated as a lead prioritization workflow, not as an autonomous final classifier.

## Role of LLM methods

LLM methods are evaluated as potential improvements over deterministic and classical ML baselines.

The expected value of LLMs is not only binary classification.

The expected value is strongest in:

1. distinguishing confirmed implementation from planning or concepts
2. detecting needs_review cases
3. reducing false positives in high ranked leads
4. identifying hidden TLM triggers from full source context
5. generating concise evidence based review notes
6. supporting three class triage

LLMs must be compared against deterministic scoring and TF IDF Logistic Regression.

A useful LLM result must improve review workflow quality, not only produce a higher global score.

## Current local LLM results

Local Hugging Face instruction tuned LLMs were evaluated on the frozen triage test split.

The same structured model outputs were mapped to strict binary relevance, actionable binary lead detection, and three class triage.

| Method | Prompt | Strict precision | Strict recall | Strict F1 | Actionable precision | Actionable recall | Actionable F1 | Triage accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 7B Instruct | hierarchical | 1.000 | 0.640 | 0.780 | 1.000 | 0.548 | 0.708 | 0.671 |
| Qwen2.5 7B Instruct | direct | 1.000 | 0.600 | 0.750 | 1.000 | 0.619 | 0.765 | 0.657 |
| Llama 3.1 8B Instruct | hierarchical | 0.929 | 0.520 | 0.667 | 0.923 | 0.571 | 0.706 | 0.586 |
| Qwen2.5 14B Instruct | hierarchical | 1.000 | 0.120 | 0.214 | 0.969 | 0.738 | 0.838 | 0.571 |

The tested local LLMs produced stable structured output.

However, they did not outperform TF IDF Logistic Regression on the frozen binary evaluation tasks.

The main pattern is high precision and lower recall.

Qwen2.5 7B is very conservative and misses many actionable cases.

Qwen2.5 14B improves actionable lead detection by assigning more cases to needs_review, but it often degrades confirmed_relevant cases to needs_review.

This makes local LLMs less suitable as standalone lead discovery models.

Their more plausible role is hybrid review support:

1. evidence extraction
2. explanation generation
3. precision filtering of high ranked leads
4. triage support for candidates already selected by score or classical ML

## Current hybrid lead selection results

Hybrid lead selection was evaluated on the aligned triage test split.

The target is actionable lead detection.

Positive actionable leads are `confirmed_relevant` and `needs_review`.

The evaluated modes include:

1. `score_only`
2. `tfidf_only`
3. `llm_only`
4. `score_or_tfidf`
5. `hybrid_weighted`
6. `hybrid_recall_guard`

The comparison was run with Qwen2.5 14B hierarchical as an upper bound LLM signal and Qwen2.5 7B variants as more production oriented LLM signals.

Main results by review depth:

| Review depth | Best mode | Precision at N | Recall at N | False negatives | Interpretation |
|---:|---|---:|---:|---:|---|
| 10 | `tfidf_only` | 1.000 | 0.238 | 32 | small high precision queue, no hybrid advantage |
| 20 | `hybrid_recall_guard` | 1.000 | 0.476 | 22 | best small review queue prioritization |
| 50 | `score_or_tfidf` | 0.780 | 0.929 | 3 | best high recall review strategy |
| 70 | `score_or_tfidf` | 0.600 | 1.000 | 0 | full test set, no workload reduction |

The recommended current hybrid strategy is:

1. use `score_or_tfidf` as the high recall candidate selection layer
2. use a production feasible local LLM such as Qwen2.5 7B for evidence generation, triage notes, and optional priority support
3. treat Qwen2.5 14B as an upper bound evaluation signal, not as the default production model

The high recall gain at broader review depth mainly comes from combining the deterministic thematic score and TF IDF probability.

The LLM adds most value as evidence and prioritization support.

An LLM prediction of `not_relevant` should not be used as a hard exclusion signal.

The remaining false negatives at top 50 are mostly broad or aggregated government communication pages where the relevant TLM signal is not prominent enough for the current score, TF IDF, or LLM signals.

## Production interpretation

A productive ChangeScout workflow should remain human in the loop.

A likely workflow is:

1. run monitoring pipeline
2. generate scored candidates
3. prioritize leads
4. attach context and optional location hints
5. let domain experts review the highest ranked leads
6. decide manually whether TLM follow up is required

The system should support expert review.

It should not automatically edit TLM.

## Current dataset status

The frozen expanded annotation dataset contains 348 manually reviewed sources.

Current class distribution:

| Class | Count |
|---|---:|
| confirmed_relevant | 124 |
| needs_review | 84 |
| not_relevant | 140 |

The dataset is suitable for MVP evaluation and CAS level method comparison.

The dataset is not large enough for strong claims about canton independent generalization.

Results must therefore be interpreted as an exploratory but reproducible evaluation.

## Scope limitation

The operational MVP runs one active canton per configured monitoring run.

The evaluation corpus contains multiple cantons to test robustness across different official source styles.

This does not change the operational runtime design.

## Success criterion

ChangeScout is successful if it reduces the amount of irrelevant source material that a reviewer must inspect while preserving most confirmed relevant and review worthy cases.

The preferred outcome is a reliable review queue, not a fully automated relevance decision.

The current results support this framing.

On task specific binary splits, TF IDF Logistic Regression is the strongest learned non LLM baseline.

On the aligned triage test split, thematic_score is strongest for strict confirmed relevance by F1.

For actionable lead selection at broader review depth, the strongest current strategy is the `score_or_tfidf` union.

The deterministic score baseline remains useful because it is transparent and does not require training data.

Local LLMs are currently more useful as review support components than as standalone lead detectors.

The preferred production oriented design is therefore a hybrid workflow: high recall candidate selection by score and TF IDF, followed by LLM based evidence generation and optional priority support.
