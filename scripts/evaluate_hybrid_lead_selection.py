from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_TRIAGE_DATASET = Path("data/annotation/evaluation/triage_3class_dataset.csv")
DEFAULT_TFIDF_PREDICTIONS = Path("data/annotation/evaluation/aligned_method_comparison/aligned_tfidf_predictions.csv")
DEFAULT_LLM_PREDICTIONS = Path("data/annotation/evaluation/local_llm/Qwen__Qwen2.5-14B-Instruct/hierarchical/llm_triage_predictions.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/annotation/evaluation/hybrid_lead_selection")

AT_N_VALUES = [10, 20, 50, 70]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def get_score_column(df: pd.DataFrame) -> str:
    if "score" in df.columns:
        return "score"

    if "thematic_score" in df.columns:
        return "thematic_score"

    raise ValueError("Expected either score or thematic_score column")


def normalize_score(series: pd.Series) -> pd.Series:
    values = series.fillna(0).astype(float)
    min_value = values.min()
    max_value = values.max()

    if max_value == min_value:
        return pd.Series([0.0] * len(values), index=values.index)

    return (values - min_value) / (max_value - min_value)


def llm_signal(value: str) -> float:
    if value == "confirmed_relevant":
        return 1.0

    if value == "needs_review":
        return 0.8

    return 0.0


def llm_actionable(value: str) -> int:
    return 1 if value in {"confirmed_relevant", "needs_review"} else 0


def load_base_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = [
        "annotation_id",
        "split",
        "triage_class",
        "source_id",
        "url",
        "title",
    ]

    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")

    score_column = get_score_column(df)

    df = df[df["split"] == "test"].copy()
    df["target_actionable"] = df["triage_class"].isin(["confirmed_relevant", "needs_review"]).astype(int)
    df["target_strict"] = (df["triage_class"] == "confirmed_relevant").astype(int)
    df["thematic_score_eval"] = df[score_column].fillna(0).astype(float)
    df["thematic_score_norm"] = normalize_score(df["thematic_score_eval"])

    return df


def load_tfidf_predictions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    df = df[df["task"] == "actionable_binary"].copy()

    required = ["annotation_id", "probability", "prediction"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")

    return df[["annotation_id", "probability", "prediction"]].rename(
        columns={
            "probability": "tfidf_actionable_probability",
            "prediction": "tfidf_actionable_prediction",
        }
    )


def load_llm_predictions(path: Path) -> pd.DataFrame:
    records = load_jsonl(path)
    df = pd.DataFrame(records)

    required = ["annotation_id", "triage_class", "notes", "evidence"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")

    output = df[["annotation_id", "triage_class", "notes", "evidence"]].copy()
    output = output.rename(
        columns={
            "triage_class": "llm_triage_class",
            "notes": "llm_notes",
            "evidence": "llm_evidence",
        }
    )

    output["llm_actionable_signal"] = output["llm_triage_class"].map(llm_signal)
    output["llm_actionable_prediction"] = output["llm_triage_class"].map(llm_actionable)

    return output


def merge_inputs(
    base_df: pd.DataFrame,
    tfidf_df: pd.DataFrame,
    llm_df: pd.DataFrame,
) -> pd.DataFrame:
    df = base_df.merge(tfidf_df, on="annotation_id", how="left")
    df = df.merge(llm_df, on="annotation_id", how="left")

    if df["tfidf_actionable_probability"].isna().any():
        missing = df[df["tfidf_actionable_probability"].isna()]["annotation_id"].tolist()
        raise ValueError(f"Missing TF IDF predictions for annotations: {missing}")

    if df["llm_triage_class"].isna().any():
        missing = df[df["llm_triage_class"].isna()]["annotation_id"].tolist()
        raise ValueError(f"Missing LLM predictions for annotations: {missing}")

    return df


def assign_priority(row: pd.Series) -> str:
    score = float(row["thematic_score_norm"])
    tfidf = float(row["tfidf_actionable_probability"])
    llm_class = str(row["llm_triage_class"])

    llm_is_actionable = llm_class in {"confirmed_relevant", "needs_review"}

    if tfidf >= 0.50 and llm_is_actionable:
        return "high"

    if score >= 0.25 and tfidf >= 0.50:
        return "high"

    if tfidf >= 0.50:
        return "medium"

    if score >= 0.25 and llm_is_actionable:
        return "medium"

    if score >= 0.05 or tfidf >= 0.35:
        return "low"

    return "excluded"


def lead_reason(row: pd.Series, mode: str) -> str:
    reasons = []

    score = float(row["thematic_score_norm"])
    tfidf = float(row["tfidf_actionable_probability"])
    llm_class = str(row["llm_triage_class"])

    if score >= 0.25:
        reasons.append("high thematic_score")
    elif score >= 0.05:
        reasons.append("weak thematic_score")

    if tfidf >= 0.50:
        reasons.append("TF IDF predicts actionable")
    elif tfidf >= 0.35:
        reasons.append("TF IDF uncertainty band")

    if llm_class in {"confirmed_relevant", "needs_review"}:
        reasons.append(f"LLM triage {llm_class}")
    else:
        reasons.append("LLM triage not_relevant, used only as downgrade signal")

    if not reasons:
        reasons.append("low score across all signals")

    return f"{mode}: " + "; ".join(reasons)


def add_mode_scores(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["score_only_rank_score"] = result["thematic_score_norm"]
    result["tfidf_only_rank_score"] = result["tfidf_actionable_probability"]
    result["llm_only_rank_score"] = result["llm_actionable_signal"]

    result["score_or_tfidf_rank_score"] = result[
        ["thematic_score_norm", "tfidf_actionable_probability"]
    ].max(axis=1)

    result["hybrid_weighted_rank_score"] = (
        0.35 * result["thematic_score_norm"]
        + 0.45 * result["tfidf_actionable_probability"]
        + 0.20 * result["llm_actionable_signal"]
    )

    result["hybrid_recall_guard_rank_score"] = result["hybrid_weighted_rank_score"]

    guard_mask = (
        (result["tfidf_actionable_probability"] >= 0.50)
        | (result["thematic_score_norm"] >= 0.25)
        | (
            (result["thematic_score_norm"] >= 0.05)
            & (result["llm_triage_class"].isin(["confirmed_relevant", "needs_review"]))
        )
    )

    result.loc[guard_mask, "hybrid_recall_guard_rank_score"] += 0.25

    result["final_review_priority"] = result.apply(assign_priority, axis=1)

    return result


def evaluate_at_n(df: pd.DataFrame, mode: str, n: int) -> dict[str, Any]:
    rank_column = f"{mode}_rank_score"

    if rank_column not in df.columns:
        raise ValueError(f"Missing rank column: {rank_column}")

    ranked = df.sort_values(
        [rank_column, "title", "url"],
        ascending=[False, True, True],
    ).copy()

    selected = ranked.head(min(n, len(ranked))).copy()

    total_records = len(ranked)
    total_positives = int(ranked["target_actionable"].sum())

    true_positives = int(selected["target_actionable"].sum())
    false_positives = int((selected["target_actionable"] == 0).sum())
    false_negatives = int(total_positives - true_positives)

    precision_at_n = true_positives / len(selected) if len(selected) else 0.0
    recall_at_n = true_positives / total_positives if total_positives else 0.0
    workload_fraction = len(selected) / total_records if total_records else 0.0
    workload_reduction = 1.0 - workload_fraction

    return {
        "mode": mode,
        "n": int(n),
        "records_total": int(total_records),
        "selected_count": int(len(selected)),
        "total_actionable": int(total_positives),
        "true_positives_at_n": true_positives,
        "false_positives_at_n": false_positives,
        "false_negatives_after_n": false_negatives,
        "precision_at_n": precision_at_n,
        "recall_at_n": recall_at_n,
        "workload_fraction": workload_fraction,
        "workload_reduction": workload_reduction,
    }


def build_leads(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    rank_column = f"{mode}_rank_score"

    leads = df.sort_values(
        [rank_column, "title", "url"],
        ascending=[False, True, True],
    ).copy()

    leads["mode"] = mode
    leads["rank"] = range(1, len(leads) + 1)
    leads["confidence_proxy"] = leads[rank_column]
    leads["lead_reason"] = leads.apply(lambda row: lead_reason(row, mode), axis=1)

    columns = [
        "mode",
        "rank",
        "annotation_id",
        "source_id",
        "url",
        "title",
        "triage_class",
        "target_actionable",
        "thematic_score_eval",
        "thematic_score_norm",
        "tfidf_actionable_probability",
        "tfidf_actionable_prediction",
        "llm_triage_class",
        "llm_actionable_signal",
        "confidence_proxy",
        "final_review_priority",
        "lead_reason",
        "llm_evidence",
        "llm_notes",
    ]

    return leads[columns]


def build_markdown_report(metrics: pd.DataFrame, output_dir: Path) -> str:
    lines = [
        "# Hybrid Lead Selection Evaluation",
        "",
        "## Scope",
        "",
        "This report evaluates lead selection strategies on the frozen aligned triage test split.",
        "",
        "The target is actionable lead detection.",
        "",
        "Positive actionable leads are confirmed_relevant and needs_review.",
        "",
        "LLM predictions are used as enrichment and reprioritization signals.",
        "",
        "LLM not_relevant predictions are not used as hard exclusion signals.",
        "",
        "## Metrics",
        "",
        "| Mode | N | Precision at N | Recall at N | False negatives after N | Workload reduction |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    ordered = metrics.sort_values(["n", "recall_at_n", "precision_at_n"], ascending=[True, False, False])

    for _, row in ordered.iterrows():
        lines.append(
            "| "
            f"{row['mode']} | "
            f"{int(row['n'])} | "
            f"{row['precision_at_n']:.3f} | "
            f"{row['recall_at_n']:.3f} | "
            f"{int(row['false_negatives_after_n'])} | "
            f"{row['workload_reduction']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The useful hybrid strategy is the one that improves recall at practical review depth without relying on the LLM as a hard filter.",
            "",
            "A high precision LLM signal can improve priority ordering and evidence quality.",
            "",
            "However, because local LLM false negatives remain frequent, LLM not_relevant should only downgrade a lead and should not remove it when score or TF IDF signals are strong.",
            "",
            "## Output files",
            "",
            f"* `{output_dir / 'hybrid_lead_selection_metrics.csv'}`",
            f"* `{output_dir / 'hybrid_leads.csv'}`",
            f"* `{output_dir / 'hybrid_lead_selection_report.md'}`",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate hybrid lead selection strategies.")
    parser.add_argument("--triage-dataset", default=str(DEFAULT_TRIAGE_DATASET))
    parser.add_argument("--tfidf-predictions", default=str(DEFAULT_TFIDF_PREDICTIONS))
    parser.add_argument("--llm-predictions", default=str(DEFAULT_LLM_PREDICTIONS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_df = load_base_dataset(Path(args.triage_dataset))
    tfidf_df = load_tfidf_predictions(Path(args.tfidf_predictions))
    llm_df = load_llm_predictions(Path(args.llm_predictions))

    df = merge_inputs(base_df, tfidf_df, llm_df)
    df = add_mode_scores(df)

    modes = [
        "score_only",
        "tfidf_only",
        "llm_only",
        "score_or_tfidf",
        "hybrid_weighted",
        "hybrid_recall_guard",
    ]

    metric_rows = []

    for mode in modes:
        for n in AT_N_VALUES:
            metric_rows.append(evaluate_at_n(df, mode, n))

    metrics = pd.DataFrame(metric_rows)

    leads = pd.concat(
        [build_leads(df, mode) for mode in modes],
        ignore_index=True,
    )

    metrics_path = output_dir / "hybrid_lead_selection_metrics.csv"
    leads_path = output_dir / "hybrid_leads.csv"
    report_path = output_dir / "hybrid_lead_selection_report.md"
    enriched_records_path = output_dir / "hybrid_eval_records.csv"

    metrics.to_csv(metrics_path, index=False, encoding="utf-8")
    leads.to_csv(leads_path, index=False, encoding="utf-8")
    df.to_csv(enriched_records_path, index=False, encoding="utf-8")
    report_path.write_text(build_markdown_report(metrics, output_dir), encoding="utf-8")

    print(f"Wrote {metrics_path}")
    print(f"Wrote {leads_path}")
    print(f"Wrote {enriched_records_path}")
    print(f"Wrote {report_path}")
    print()
    print(metrics.sort_values(["n", "recall_at_n", "precision_at_n"], ascending=[True, False, False]).to_string(index=False))


if __name__ == "__main__":
    main()
