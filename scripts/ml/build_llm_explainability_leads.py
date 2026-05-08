from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_LEADS = Path("results/evaluation/hybrid_lead_selection_qwen7b_direct/hybrid_leads.csv")
DEFAULT_RECORDS = Path("results/evaluation/hybrid_lead_selection_qwen7b_direct/hybrid_eval_records.csv")
DEFAULT_OUTPUT_DIR = Path("results/evaluation/llm_explainability")


EVIDENCE_TYPES = {
    "confirmed_geometry",
    "plausible_review_signal",
    "no_geometry_evidence",
    "unclear",
}


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""

    return str(value).strip()


def infer_evidence_type(row: pd.Series) -> str:
    triage_class = normalize_text(row.get("llm_triage_class"))

    if triage_class == "confirmed_relevant":
        return "confirmed_geometry"

    if triage_class == "needs_review":
        return "plausible_review_signal"

    if triage_class == "not_relevant":
        return "no_geometry_evidence"

    return "unclear"


def build_explanation_note(row: pd.Series) -> str:
    triage_class = normalize_text(row.get("llm_triage_class"))
    llm_notes = normalize_text(row.get("llm_notes"))
    gold_class = normalize_text(row.get("triage_class"))

    if llm_notes:
        note = llm_notes
    elif triage_class == "confirmed_relevant":
        note = "The LLM identified confirmed geometry evidence in the source text."
    elif triage_class == "needs_review":
        note = "The LLM identified a plausible review signal, but not enough confirmed geometry evidence."
    elif triage_class == "not_relevant":
        note = "The LLM did not identify confirmed or plausible TLM geometry evidence."
    else:
        note = "The LLM output was unclear."

    if gold_class and gold_class != triage_class:
        note = (
            note
            + " Audit note: model triage differs from the frozen annotation label."
        )

    return note


def build_evidence_snippet(row: pd.Series) -> str:
    evidence = normalize_text(row.get("llm_evidence"))

    if evidence:
        return evidence

    return ""


def build_audit_flags(row: pd.Series) -> dict[str, Any]:
    evidence_snippet = normalize_text(row.get("evidence_snippet"))
    llm_class = normalize_text(row.get("llm_triage_class"))
    gold_class = normalize_text(row.get("triage_class"))

    return {
        "missing_evidence_snippet": evidence_snippet == "",
        "llm_gold_disagreement": bool(gold_class and llm_class and gold_class != llm_class),
        "llm_predicted_not_relevant_for_selected_lead": llm_class == "not_relevant",
        "requires_manual_explanation_check": (
            evidence_snippet == ""
            or bool(gold_class and llm_class and gold_class != llm_class)
            or llm_class == "not_relevant"
        ),
    }


def load_selected_leads(
    leads_path: Path,
    records_path: Path,
    mode: str,
    top_n: int,
) -> pd.DataFrame:
    leads = pd.read_csv(leads_path)
    records = pd.read_csv(records_path)

    selected = (
        leads[leads["mode"] == mode]
        .sort_values("rank")
        .head(top_n)
        .copy()
    )

    if selected.empty:
        raise ValueError(f"No selected leads found for mode={mode}")

    merge_columns = [
        "annotation_id",
        "text_full",
        "change_type",
        "notes",
        "target_strict",
        "target_actionable",
    ]

    available_merge_columns = [
        column for column in merge_columns if column in records.columns
    ]

    selected = selected.merge(
        records[available_merge_columns],
        on="annotation_id",
        how="left",
        suffixes=("", "_record"),
    )

    return selected


def enrich_explanations(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["evidence_type"] = result.apply(infer_evidence_type, axis=1)
    result["explanation_note"] = result.apply(build_explanation_note, axis=1)
    result["evidence_snippet"] = result.apply(build_evidence_snippet, axis=1)

    audit_flags = result.apply(build_audit_flags, axis=1)
    audit_df = pd.DataFrame(audit_flags.tolist())

    for column in audit_df.columns:
        result[column] = audit_df[column]

    result["explanation_source"] = "existing_local_llm_triage_output"
    result["explanation_is_selection_signal"] = False

    return result


def summarize(df: pd.DataFrame, mode: str, top_n: int) -> dict[str, Any]:
    return {
        "mode": mode,
        "top_n": int(top_n),
        "records": int(len(df)),
        "evidence_type_counts": df["evidence_type"].value_counts().to_dict(),
        "llm_triage_counts": df["llm_triage_class"].value_counts().to_dict(),
        "gold_triage_counts": df["triage_class"].value_counts().to_dict(),
        "missing_evidence_snippet_count": int(df["missing_evidence_snippet"].sum()),
        "llm_gold_disagreement_count": int(df["llm_gold_disagreement"].sum()),
        "llm_predicted_not_relevant_for_selected_lead_count": int(
            df["llm_predicted_not_relevant_for_selected_lead"].sum()
        ),
        "requires_manual_explanation_check_count": int(
            df["requires_manual_explanation_check"].sum()
        ),
    }


def build_markdown_report(summary: dict[str, Any], output_dir: Path) -> str:
    lines = [
        "# LLM Explainability Output Evaluation",
        "",
        "## Scope",
        "",
        "This report evaluates explanation fields for selected ChangeScout leads.",
        "",
        "The selected leads come from the hybrid lead selection workflow.",
        "",
        "The LLM explanation is used for review support only.",
        "",
        "It is not used as a hard exclusion signal and does not change candidate selection.",
        "",
        "## Input selection",
        "",
        f"* Mode: `{summary['mode']}`",
        f"* Top N: `{summary['top_n']}`",
        f"* Records: `{summary['records']}`",
        "",
        "## Evidence type counts",
        "",
        "| Evidence type | Count |",
        "|---|---:|",
    ]

    for key, value in sorted(summary["evidence_type_counts"].items()):
        lines.append(f"| {key} | {int(value)} |")

    lines.extend(
        [
            "",
            "## LLM triage counts",
            "",
            "| LLM triage class | Count |",
            "|---|---:|",
        ]
    )

    for key, value in sorted(summary["llm_triage_counts"].items()):
        lines.append(f"| {key} | {int(value)} |")

    lines.extend(
        [
            "",
            "## Audit flags",
            "",
            f"* Missing evidence snippets: `{summary['missing_evidence_snippet_count']}`",
            f"* LLM versus gold disagreement: `{summary['llm_gold_disagreement_count']}`",
            f"* LLM predicted not_relevant for selected lead: `{summary['llm_predicted_not_relevant_for_selected_lead_count']}`",
            f"* Requires manual explanation check: `{summary['requires_manual_explanation_check_count']}`",
            "",
            "## Interpretation",
            "",
            "The explainability output makes selected leads easier to inspect without changing the high recall selection logic.",
            "",
            "The audit flags identify leads where the explanation should be checked manually before it is trusted.",
            "",
            "In particular, LLM not_relevant predictions for selected leads must not remove the lead.",
            "",
            "They only signal that the generated explanation may be weak or that the lead requires closer manual review.",
            "",
            "## Output files",
            "",
            f"* `{output_dir / 'llm_explainability_leads.csv'}`",
            f"* `{output_dir / 'llm_explainability_leads.jsonl'}`",
            f"* `{output_dir / 'llm_explainability_report.json'}`",
            f"* `{output_dir / 'llm_explainability_report.md'}`",
            "",
        ]
    )

    return "\n".join(lines)


def write_jsonl(path: Path, df: pd.DataFrame) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in df.to_dict(orient="records"):
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build LLM explainability outputs for selected leads.")
    parser.add_argument("--leads", default=str(DEFAULT_LEADS))
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    parser.add_argument("--mode", default="score_or_tfidf")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = load_selected_leads(
        leads_path=Path(args.leads),
        records_path=Path(args.records),
        mode=args.mode,
        top_n=args.top_n,
    )

    enriched = enrich_explanations(selected)
    report = summarize(enriched, mode=args.mode, top_n=args.top_n)

    csv_path = output_dir / "llm_explainability_leads.csv"
    jsonl_path = output_dir / "llm_explainability_leads.jsonl"
    report_json_path = output_dir / "llm_explainability_report.json"
    report_md_path = output_dir / "llm_explainability_report.md"

    enriched.to_csv(csv_path, index=False, encoding="utf-8")
    write_jsonl(jsonl_path, enriched)

    report_json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report_md_path.write_text(
        build_markdown_report(report, output_dir),
        encoding="utf-8",
    )

    print(f"Wrote {csv_path}")
    print(f"Wrote {jsonl_path}")
    print(f"Wrote {report_json_path}")
    print(f"Wrote {report_md_path}")
    print()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
