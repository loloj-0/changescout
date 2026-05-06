from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


OUTPUT_DIR = Path("data/annotation/evaluation/report_package")

PATHS = {
    "triage_dataset": Path("data/annotation/evaluation/triage_3class_dataset.csv"),
    "strict_dataset": Path("data/annotation/evaluation/strict_binary_dataset.csv"),
    "actionable_dataset": Path("data/annotation/evaluation/actionable_binary_dataset.csv"),
    "aligned_comparison": Path("data/annotation/evaluation/aligned_method_comparison/aligned_method_comparison.csv"),
    "local_llm_comparison": Path("data/annotation/evaluation/local_llm/comparison/local_llm_comparison.csv"),
    "hybrid_comparison": Path("data/annotation/evaluation/hybrid_lead_selection_comparison/hybrid_lead_selection_comparison.csv"),
    "explainability_report": Path("data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated_report.json"),
    "explainability_notes": Path("data/annotation/evaluation/llm_explainability_generated/explainability_manual_review_notes.md"),
    "score_report": Path("data/annotation/evaluation/score_baseline/score_baseline_report.md"),
    "classifier_report": Path("data/annotation/evaluation/classical_text_classifier/classical_text_classifier_report.md"),
    "local_llm_report": Path("data/annotation/evaluation/local_llm/comparison/local_llm_comparison.md"),
    "aligned_report": Path("data/annotation/evaluation/aligned_method_comparison/aligned_method_comparison.md"),
    "hybrid_report": Path("data/annotation/evaluation/hybrid_lead_selection_comparison/hybrid_lead_selection_comparison.md"),
    "llm_error_analysis": Path("data/annotation/evaluation/local_llm/error_analysis/llm_triage_error_analysis.md"),
    "score_or_tfidf_false_negatives": Path("data/annotation/evaluation/hybrid_lead_selection_comparison/score_or_tfidf_top50_false_negatives.md"),
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8")


def build_dataset_summary() -> pd.DataFrame:
    frames = []

    for name, path_key in [
        ("strict_binary", "strict_dataset"),
        ("actionable_binary", "actionable_dataset"),
        ("triage_3class", "triage_dataset"),
    ]:
        df = read_csv(PATHS[path_key])

        row = {
            "dataset": name,
            "records": int(len(df)),
            "train_records": int((df["split"] == "train").sum()),
            "test_records": int((df["split"] == "test").sum()),
        }

        for split in ["train", "test", "all"]:
            part = df if split == "all" else df[df["split"] == split]
            counts = part["triage_class"].value_counts().to_dict()
            for label in ["confirmed_relevant", "needs_review", "not_relevant"]:
                row[f"{split}_{label}"] = int(counts.get(label, 0))

        frames.append(row)

    return pd.DataFrame(frames)


def build_core_method_table() -> pd.DataFrame:
    aligned = read_csv(PATHS["aligned_comparison"])

    keep = [
        "task",
        "method",
        "method_type",
        "records",
        "positives",
        "negatives",
        "precision",
        "recall",
        "f1",
        "accuracy",
        "tp",
        "fp",
        "tn",
        "fn",
    ]

    available = [column for column in keep if column in aligned.columns]
    table = aligned[available].copy()

    table = table.sort_values(
        ["task", "f1", "recall", "precision"],
        ascending=[True, False, False, False],
    )

    return table


def build_llm_table() -> pd.DataFrame:
    df = read_csv(PATHS["local_llm_comparison"])

    keep = [
        "model_id",
        "prompt_variant",
        "records",
        "parse_success_rate",
        "strict_precision",
        "strict_recall",
        "strict_f1",
        "actionable_precision",
        "actionable_recall",
        "actionable_f1",
        "triage_accuracy",
    ]

    available = [column for column in keep if column in df.columns]
    return df[available].copy()


def build_hybrid_summary() -> pd.DataFrame:
    df = read_csv(PATHS["hybrid_comparison"])

    preferred_rows = []

    for n in [10, 20, 50, 70]:
        subset = df[df["n"] == n].copy()
        if subset.empty:
            continue

        mode_preference = {
            "score_or_tfidf": 0,
            "tfidf_only": 1,
            "score_only": 2,
            "hybrid_recall_guard": 3,
            "hybrid_weighted": 4,
            "llm_only": 5,
        }

        subset["mode_preference"] = subset["mode"].map(mode_preference).fillna(99)

        subset = subset.sort_values(
            ["recall_at_n", "precision_at_n", "false_negatives_after_n", "mode_preference", "mode"],
            ascending=[False, False, True, True, True],
        )

        best = subset.iloc[0].to_dict()

        if best.get("mode") in {"score_only", "tfidf_only", "score_or_tfidf"}:
            best["llm_run"] = "not_applicable"

        preferred_rows.append(best)

    preferred = pd.DataFrame(preferred_rows)

    keep = [
        "n",
        "mode",
        "llm_run",
        "records_total",
        "selected_count",
        "total_actionable",
        "true_positives_at_n",
        "false_positives_at_n",
        "false_negatives_after_n",
        "precision_at_n",
        "recall_at_n",
        "workload_fraction",
        "workload_reduction",
    ]

    available = [column for column in keep if column in preferred.columns]
    return preferred[available].copy()


def build_explainability_summary() -> pd.DataFrame:
    report = read_json(PATHS["explainability_report"])

    rows = [
        {"metric": "records", "value": report.get("records")},
        {"metric": "parse_success_rate", "value": report.get("parse_success_rate")},
        {"metric": "missing_evidence_snippet_count", "value": report.get("missing_evidence_snippet_count")},
        {"metric": "evidence_snippet_found_in_source_count", "value": report.get("evidence_snippet_found_in_source_count")},
        {"metric": "requires_manual_explanation_check_count", "value": report.get("requires_manual_explanation_check_count")},
    ]

    for evidence_type, count in report.get("evidence_type_counts", {}).items():
        rows.append({"metric": f"evidence_type_{evidence_type}", "value": count})

    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows).copy()

    if df.empty:
        return ""

    table = df.copy()
    table = table.fillna("")

    columns = [str(column) for column in table.columns]

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]

    for _, row in table.iterrows():
        values = []
        for column in table.columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def build_artifact_index() -> str:
    lines = [
        "# Evaluation Report Package Artifact Index",
        "",
        "This file lists the source artifacts used to build the report package.",
        "",
        "| Key | Path | Exists |",
        "|---|---|---:|",
    ]

    for key, path in PATHS.items():
        lines.append(f"| {key} | `{path}` | {path.exists()} |")

    lines.append("")
    return "\n".join(lines)


def build_limitations() -> str:
    return """# Evaluation Limitations

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
"""


def build_recommended_setup() -> str:
    return """# Recommended Setup

The recommended current setup is a human in the loop review workflow.

Candidate selection should use `score_or_tfidf`.

This combines deterministic thematic scoring and TF IDF actionable probability.

For the aligned triage test split, the top 50 `score_or_tfidf` review queue reached high actionable recall with limited workload.

The LLM should be used after candidate selection.

The recommended LLM role is evidence generation, explanation, triage notes, and optional priority support.

A production feasible model such as Qwen2.5 7B is preferred for this support layer.

Qwen2.5 14B is useful for comparison, but not required as default production model.

LLM predictions must not be used as hard exclusion signals.

The explanation layer should attach audit fields to each generated explanation.

Reviewers should treat the explanation as support, not as authoritative proof.
"""


def build_summary_md(
    dataset_summary: pd.DataFrame,
    method_table: pd.DataFrame,
    llm_table: pd.DataFrame,
    hybrid_summary: pd.DataFrame,
    explainability_summary: pd.DataFrame,
) -> str:
    actionable = method_table[method_table["task"] == "actionable_binary"].copy()
    strict = method_table[method_table["task"] == "strict_binary"].copy()

    lines = [
        "# Evaluation Report Package",
        "",
        "## Purpose",
        "",
        "This package consolidates the current ChangeScout evaluation artifacts into report ready tables and interpretation notes.",
        "",
        "It does not run new models.",
        "",
        "It reads stored evaluation artifacts and rewrites a reproducible result package.",
        "",
        "## Dataset summary",
        "",
        markdown_table(dataset_summary),
        "",
        "## Aligned method comparison",
        "",
        "All methods in this table are evaluated on the same frozen triage test records.",
        "",
        markdown_table(method_table),
        "",
        "## Strict binary comparison",
        "",
        "Strict binary excludes needs_review cases and evaluates confirmed relevance only.",
        "",
        markdown_table(strict),
        "",
        "## Actionable binary comparison",
        "",
        "Actionable binary maps confirmed_relevant and needs_review to positive.",
        "",
        markdown_table(actionable),
        "",
        "## Local LLM comparison",
        "",
        markdown_table(llm_table),
        "",
        "## Hybrid lead selection summary",
        "",
        "This table shows the preferred mode by review depth according to recall, precision, false negatives, and mode preference.",
        "",
        markdown_table(hybrid_summary),
        "",
        "## LLM explainability summary",
        "",
        markdown_table(explainability_summary),
        "",
        "## Main interpretation",
        "",
        "The deterministic thematic score remains the strongest strict confirmed relevance baseline on aligned records.",
        "",
        "TF IDF Logistic Regression provides strong recall for actionable lead detection.",
        "",
        "Qwen2.5 14B hierarchical achieves the highest actionable F1 among evaluated LLM runs, but it is weak for strict confirmed relevance because many confirmed cases are downgraded to needs_review.",
        "",
        "Qwen2.5 14B direct is part of the direct versus hierarchical prompt comparison and does not improve over Qwen2.5 14B hierarchical.",
        "",
        "Qwen2.5 7B variants are more production oriented and useful for evidence generation and review support.",
        "",
        "The recommended lead selection strategy is score_or_tfidf candidate selection followed by LLM based explanation support.",
        "",
        "LLM predictions are not hard exclusion signals.",
        "",
        "## Output files in this package",
        "",
        "* `dataset_summary.csv`",
        "* `method_comparison_aligned.csv`",
        "* `local_llm_comparison.csv`",
        "* `hybrid_summary.csv`",
        "* `explainability_summary.csv`",
        "* `artifact_index.md`",
        "* `limitations.md`",
        "* `recommended_setup.md`",
        "",
        "## Source reports for detailed inspection",
        "",
        "Detailed confusion matrices, threshold selection reports, qualitative error analysis, and false negative examples are available in the source artifacts listed in `artifact_index.md`.",
        "",
        "The package intentionally keeps derived summary tables separate from detailed source reports to avoid duplicating long outputs.",
        "",
        "Key detailed reports:",
        "",
        "* `data/annotation/evaluation/aligned_method_comparison/aligned_method_comparison.md`",
        "* `data/annotation/evaluation/local_llm/comparison/local_llm_comparison.md`",
        "* `data/annotation/evaluation/hybrid_lead_selection_comparison/hybrid_lead_selection_comparison.md`",
        "* `data/annotation/evaluation/local_llm/error_analysis/llm_triage_error_analysis.md`",
        "* `data/annotation/evaluation/hybrid_lead_selection_comparison/score_or_tfidf_top50_false_negatives.md`",
        "* `data/annotation/evaluation/llm_explainability_generated/explainability_manual_review_notes.md`",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset_summary = build_dataset_summary()
    method_table = build_core_method_table()
    llm_table = build_llm_table()
    hybrid_summary = build_hybrid_summary()
    explainability_summary = build_explainability_summary()

    write_csv(dataset_summary, OUTPUT_DIR / "dataset_summary.csv")
    write_csv(method_table, OUTPUT_DIR / "method_comparison_aligned.csv")
    write_csv(llm_table, OUTPUT_DIR / "local_llm_comparison.csv")
    write_csv(hybrid_summary, OUTPUT_DIR / "hybrid_summary.csv")
    write_csv(explainability_summary, OUTPUT_DIR / "explainability_summary.csv")

    (OUTPUT_DIR / "artifact_index.md").write_text(build_artifact_index(), encoding="utf-8")
    (OUTPUT_DIR / "limitations.md").write_text(build_limitations(), encoding="utf-8")
    (OUTPUT_DIR / "recommended_setup.md").write_text(build_recommended_setup(), encoding="utf-8")

    summary = build_summary_md(
        dataset_summary=dataset_summary,
        method_table=method_table,
        llm_table=llm_table,
        hybrid_summary=hybrid_summary,
        explainability_summary=explainability_summary,
    )

    (OUTPUT_DIR / "evaluation_report_package.md").write_text(summary, encoding="utf-8")

    print(f"Wrote {OUTPUT_DIR / 'dataset_summary.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'method_comparison_aligned.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'local_llm_comparison.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'hybrid_summary.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'explainability_summary.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'artifact_index.md'}")
    print(f"Wrote {OUTPUT_DIR / 'limitations.md'}")
    print(f"Wrote {OUTPUT_DIR / 'recommended_setup.md'}")
    print(f"Wrote {OUTPUT_DIR / 'evaluation_report_package.md'}")


if __name__ == "__main__":
    main()
