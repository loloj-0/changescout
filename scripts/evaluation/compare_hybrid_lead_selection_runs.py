from __future__ import annotations

from pathlib import Path
import pandas as pd


RUNS = {
    "qwen14b_hierarchical": Path("results/evaluation/hybrid_lead_selection/hybrid_lead_selection_metrics.csv"),
    "qwen14b_direct": Path("results/evaluation/hybrid_lead_selection_qwen14b_direct/hybrid_lead_selection_metrics.csv"),
    "qwen7b_hierarchical": Path("results/evaluation/hybrid_lead_selection_qwen7b_hierarchical/hybrid_lead_selection_metrics.csv"),
    "qwen7b_direct": Path("results/evaluation/hybrid_lead_selection_qwen7b_direct/hybrid_lead_selection_metrics.csv"),
}

OUTPUT_DIR = Path("results/evaluation/hybrid_lead_selection_comparison")


def load_runs() -> pd.DataFrame:
    frames = []

    for run_name, path in RUNS.items():
        if not path.exists():
            raise FileNotFoundError(path)

        df = pd.read_csv(path)
        df["llm_run"] = run_name
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Hybrid Lead Selection Comparison",
        "",
        "## Scope",
        "",
        "This report compares hybrid lead selection results across local LLM variants.",
        "",
        "All runs use the same frozen aligned triage test split.",
        "",
        "The target is actionable lead detection.",
        "",
        "Positive actionable leads are confirmed_relevant and needs_review.",
        "",
        "LLM predictions are used as enrichment and reprioritization signals, not as hard exclusion signals.",
        "",
        "## Metrics",
        "",
        "| LLM run | Mode | N | Precision at N | Recall at N | False negatives after N | Workload reduction |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    ordered = df.sort_values(
        ["n", "recall_at_n", "precision_at_n", "llm_run"],
        ascending=[True, False, False, True],
    )

    for _, row in ordered.iterrows():
        lines.append(
            "| "
            f"{row['llm_run']} | "
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
            "## Best modes by review depth",
            "",
            "| N | Best mode | LLM dependency | Recall | Precision | False negatives |",
            "|---:|---|---|---:|---:|---:|",
        ]
    )

    llm_independent_modes = {"score_only", "tfidf_only", "score_or_tfidf"}

    dedup_columns = [
        "n",
        "mode",
        "precision_at_n",
        "recall_at_n",
        "false_negatives_after_n",
        "workload_reduction",
    ]

    deduped = df.drop_duplicates(subset=dedup_columns).copy()

    for n in sorted(deduped["n"].unique()):
        subset = deduped[deduped["n"] == n].copy()
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
        best = subset.iloc[0]

        if best["mode"] in llm_independent_modes:
            llm_dependency = "not_applicable"
        else:
            matching_rows = df[
                (df["n"] == best["n"])
                & (df["mode"] == best["mode"])
                & (df["precision_at_n"] == best["precision_at_n"])
                & (df["recall_at_n"] == best["recall_at_n"])
                & (df["false_negatives_after_n"] == best["false_negatives_after_n"])
            ].copy()

            llm_runs = sorted(matching_rows["llm_run"].unique().tolist())
            llm_dependency = ", ".join(llm_runs)

        lines.append(
            "| "
            f"{int(n)} | "
            f"{best['mode']} | "
            f"{llm_dependency} | "
            f"{best['recall_at_n']:.3f} | "
            f"{best['precision_at_n']:.3f} | "
            f"{int(best['false_negatives_after_n'])} |"
        )

    lines.extend(
        [
            "",
            "## Findings",
            "",
            "* At top 10, TF IDF, LLM only, and hybrid variants reach perfect precision and identical recall across the evaluated LLM variants.",
            "* At top 20, LLM only and hybrid variants reach perfect precision and the highest recall.",
            "* At top 50, score_or_tfidf and hybrid variants recover the most actionable leads.",
            "* Qwen2.5 14B hierarchical is the strongest LLM signal for actionable F1, but it is not the preferred production default because it is computationally heavier and required CPU offload in the current environment.",
            "* Qwen2.5 7B variants are more production oriented and still useful for shallow priority ranking and evidence generation.",
            "* The high recall gain at broader review depth mainly comes from combining thematic_score and TF IDF probability.",
            "* LLM not_relevant predictions should not be used as hard exclusion signals.",
            "",
            "## Recommended hybrid strategy",
            "",
            "Use score_or_tfidf as the high recall candidate selection layer.",
            "",
            "Use a production feasible local LLM such as Qwen2.5 7B for evidence generation, triage notes, and optional priority support.",
            "",
            "Use Qwen2.5 14B as an upper bound evaluation signal, not as the default production model.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_runs()

    output_csv = OUTPUT_DIR / "hybrid_lead_selection_comparison.csv"
    output_md = OUTPUT_DIR / "hybrid_lead_selection_comparison.md"

    df.to_csv(output_csv, index=False, encoding="utf-8")
    output_md.write_text(build_markdown(df), encoding="utf-8")

    print(f"Wrote {output_csv}")
    print(f"Wrote {output_md}")
    print()
    print(
        df.sort_values(
            ["n", "recall_at_n", "precision_at_n", "llm_run"],
            ascending=[True, False, False, True],
        ).to_string(index=False)
    )


if __name__ == "__main__":
    main()
