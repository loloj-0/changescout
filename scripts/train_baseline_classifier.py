from __future__ import annotations

from pathlib import Path
import json

from changescout.classification import run_baseline_classification


ANNOTATION_PATH = Path("data/annotation/labeled/annotation_full_reviewed.csv")
SCORED_POOL_PATH = Path("artifacts/scored_annotation_pool.jsonl")
OUTPUT_DIR = Path("data/annotation/evaluation")

TRAIN_OUTPUT_PATH = OUTPUT_DIR / "baseline_train.csv"
TEST_OUTPUT_PATH = OUTPUT_DIR / "baseline_test.csv"
REVIEW_OUTPUT_PATH = OUTPUT_DIR / "baseline_review_set.csv"
PREDICTIONS_OUTPUT_PATH = OUTPUT_DIR / "baseline_classifier_predictions.csv"
METRICS_OUTPUT_PATH = OUTPUT_DIR / "baseline_classifier_metrics.json"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = run_baseline_classification(
        annotation_path=ANNOTATION_PATH,
        scored_pool_path=SCORED_POOL_PATH,
        test_size=0.2,
        random_state=42,
        scoring_threshold=0.10,
    )

    result["train"].to_csv(TRAIN_OUTPUT_PATH, index=False, encoding="utf-8")
    result["test"].to_csv(TEST_OUTPUT_PATH, index=False, encoding="utf-8")
    result["review_set"].to_csv(REVIEW_OUTPUT_PATH, index=False, encoding="utf-8")

    prediction_columns = [
        "document_id",
        "source_id",
        "url",
        "title",
        "tlm_relevant",
        "thematic_score",
        "classifier_prediction",
        "classifier_probability",
        "change_type",
        "notes",
    ]

    available_prediction_columns = [
        column for column in prediction_columns
        if column in result["predictions"].columns
    ]

    result["predictions"][available_prediction_columns].to_csv(
        PREDICTIONS_OUTPUT_PATH,
        index=False,
        encoding="utf-8",
    )

    write_json(METRICS_OUTPUT_PATH, result["metrics"])

    print("Baseline classification completed")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print(f"Wrote train split: {TRAIN_OUTPUT_PATH}")
    print(f"Wrote test split: {TEST_OUTPUT_PATH}")
    print(f"Wrote review set: {REVIEW_OUTPUT_PATH}")
    print(f"Wrote predictions: {PREDICTIONS_OUTPUT_PATH}")
    print(f"Wrote metrics: {METRICS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()