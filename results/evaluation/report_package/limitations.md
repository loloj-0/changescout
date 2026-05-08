# Evaluation Limitations

The evaluation package summarizes the current frozen MVP evaluation state.

The results are not a production performance guarantee.

The annotation dataset contains official canton source pages, but the source mix is still limited.

The task specific binary datasets and the aligned triage comparison answer different questions.

Task specific binary metrics evaluate each binary target on its own split.

Aligned comparison metrics evaluate all methods on the same triage test records.

The deterministic thematic score is transparent and reproducible, but it is calibrated on the current MVP source mix.

TF IDF Logistic Regression is a strong non LLM baseline, but it depends on the current labels and source distribution.

Local LLMs were evaluated zero shot.

They are not fine tuned domain models.

LLM triage outputs are not stable enough for standalone automatic classification.

LLM not_relevant predictions should not remove candidates when score or TF IDF signals are strong.

LLM explanations improve reviewability, but they require audit flags and manual checking when evidence is weak or not exactly source matched.

GeoAdmin and local location hints are review aids only.

No output confirms that TLM must be updated.
