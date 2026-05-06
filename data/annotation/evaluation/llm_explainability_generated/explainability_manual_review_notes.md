# Explainability Manual Review Notes

## Scope

This note summarizes a manual inspection of generated explanation outputs for the top 50 score_or_tfidf leads.

The explanations were generated with Qwen2.5 7B Instruct using a dedicated explanation prompt.

The goal is review support, not automatic lead selection or automatic TLM confirmation.

## Summary

The dedicated explanation prompt is substantially more useful than reusing LLM triage outputs.

It produced valid structured JSON for all 50 selected leads.

No evidence snippet was missing.

45 of 50 evidence snippets were exact substrings of the source text.

19 of 50 explanations were flagged for manual checking.

## Main observed issues

Some evidence snippets are close paraphrases or composed snippets rather than exact source substrings.

Some selected leads contain weak or incomplete source text, especially pages with generic titles or limited extracted content.

Some explanations correctly extract a relevant snippet but assign an overly conservative evidence type.

Some false positive leads are correctly explained as no_geometry_evidence, which is useful for reviewer prioritization.

## Notable cases

ann_0213 is gold confirmed_relevant, but the available text in the evaluated record appears to contain mostly generic contact or publication text. The explanation therefore fails because the input text is weak.

ann_0151 contains a strong snippet about a Velostreifen becoming an abgetrennter Veloweg, but the model still assigns no_geometry_evidence. This is a reasoning error.

ann_0347 is confirmed_relevant because the source mentions redimensioning of the road, new or changed cycling infrastructure, crossing aids, and removal of an underpass. The generated explanation is useful but chooses a weaker signal than the strongest available geometry evidence.

## Interpretation

The explanation prompt improves lead usability and auditability.

However, explanation outputs must remain audit flagged and human reviewed.

The model should not be treated as an authoritative explanation layer.

Future prompt versions may include guideline aligned refinements, but this should be evaluated separately to avoid optimizing on the current test examples.
