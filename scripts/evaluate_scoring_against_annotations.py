from pathlib import Path
import json
import pandas as pd


ANNOTATION_PATH = Path("data/annotation/labeled/annotation_full_reviewed.csv")
SCORED_PATH = Path("artifacts/scored_annotation_pool.jsonl")
OUTPUT_DIR = Path("data/annotation/evaluation")


def load_jsonl(path: Path) -> pd.DataFrame:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return pd.DataFrame(records)


def normalize_bool(value):
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n"}:
        return False

    raise ValueError(f"Cannot parse boolean value: {value}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    annotations = pd.read_csv(ANNOTATION_PATH)
    scored = load_jsonl(SCORED_PATH)

    required_annotation_columns = {
        "url",
        "tlm_relevant",
        "review_required",
    }

    missing_columns = required_annotation_columns - set(annotations.columns)
    if missing_columns:
        raise ValueError(f"Missing annotation columns: {sorted(missing_columns)}")

    if "thematic_score" not in scored.columns:
        raise ValueError("Missing thematic_score in scored.jsonl")

    annotations["tlm_relevant"] = annotations["tlm_relevant"].map(normalize_bool)
    annotations["review_required"] = annotations["review_required"].map(normalize_bool)

    keep_scored_columns = [
        "url",
        "thematic_score",
        "scoring_signals",
    ]

    optional_scored_columns = [
        "title",
        "source_id",
    ]

    keep_scored_columns.extend(
        column for column in optional_scored_columns if column in scored.columns
    )

    merged = annotations.merge(
        scored[keep_scored_columns],
        on="url",
        how="left",
        suffixes=("", "_scored"),
    )

    missing_scores = merged["thematic_score"].isna().sum()
    if missing_scores:
        print(f"Warning: {missing_scores} annotated records have no matching score")

    thresholds = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]

    rows = []
    evaluable = merged[
        (merged["review_required"] == False)
        & merged["thematic_score"].notna()
    ].copy()

    for threshold in thresholds:
        predicted = evaluable["thematic_score"] >= threshold
        actual = evaluable["tlm_relevant"]

        tp = int(((predicted == True) & (actual == True)).sum())
        fp = int(((predicted == True) & (actual == False)).sum())
        tn = int(((predicted == False) & (actual == False)).sum())
        fn = int(((predicted == False) & (actual == True)).sum())

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        rows.append(
            {
                "threshold": threshold,
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )

    threshold_report = pd.DataFrame(rows)

    false_negatives = merged[
        (merged["review_required"] == False)
        & (merged["tlm_relevant"] == True)
        & (merged["thematic_score"] < 0.1)
    ].copy()

    high_false_positives = merged[
        (merged["review_required"] == False)
        & (merged["tlm_relevant"] == False)
        & (merged["thematic_score"] > 0.5)
    ].copy()

    low_true_positives = merged[
        (merged["review_required"] == False)
        & (merged["tlm_relevant"] == True)
        & (merged["thematic_score"] < 0.3)
    ].copy()

    review_cases = merged[
        merged["review_required"] == True
    ].copy()

    merged.to_csv(
        OUTPUT_DIR / "scoring_annotation_joined.csv",
        index=False,
        encoding="utf-8",
    )

    threshold_report.to_csv(
        OUTPUT_DIR / "threshold_report.csv",
        index=False,
        encoding="utf-8",
    )

    false_negatives.to_csv(
        OUTPUT_DIR / "false_negatives_score_below_0_1.csv",
        index=False,
        encoding="utf-8",
    )

    high_false_positives.to_csv(
        OUTPUT_DIR / "high_false_positives_score_above_0_5.csv",
        index=False,
        encoding="utf-8",
    )

    low_true_positives.to_csv(
        OUTPUT_DIR / "low_true_positives_score_below_0_3.csv",
        index=False,
        encoding="utf-8",
    )

    review_cases.to_csv(
        OUTPUT_DIR / "review_cases.csv",
        index=False,
        encoding="utf-8",
    )

    print("Evaluation completed")
    print(threshold_report.to_string(index=False))
    print(f"False negatives below 0.1: {len(false_negatives)}")
    print(f"High false positives above 0.5: {len(high_false_positives)}")
    print(f"Low true positives below 0.3: {len(low_true_positives)}")
    print(f"Review cases: {len(review_cases)}")


if __name__ == "__main__":
    main()