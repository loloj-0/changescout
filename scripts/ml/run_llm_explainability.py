from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_LEADS = Path("results/evaluation/hybrid_lead_selection_qwen7b_direct/hybrid_leads.csv")
DEFAULT_RECORDS = Path("results/evaluation/hybrid_lead_selection_qwen7b_direct/hybrid_eval_records.csv")
DEFAULT_OUTPUT_DIR = Path("results/evaluation/llm_explainability_generated")

VALID_EVIDENCE_TYPES = {
    "confirmed_geometry",
    "plausible_review_signal",
    "no_geometry_evidence",
    "unclear",
}


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_model_name(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "_")


def extract_json(text: str) -> tuple[dict[str, Any], str]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned.strip(), flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned.strip()).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return {}, "no_json_object_found"

    candidate = cleaned[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as error:
        return {}, f"json_decode_error: {error}"

    if not isinstance(parsed, dict):
        return {}, "json_is_not_object"

    return parsed, ""


def build_prompt(row: pd.Series) -> str:
    title = normalize_text(row.get("title"))
    text = normalize_text(row.get("text_full"))
    source_id = normalize_text(row.get("source_id"))
    score = normalize_text(row.get("thematic_score_eval"))
    tfidf = normalize_text(row.get("tfidf_actionable_probability"))

    return f"""
You are supporting a human reviewer for ChangeScout.

ChangeScout is a lead prioritization system for possible TLM road and path geometry updates.

The lead has already been selected by score or TF IDF.
Your task is not to remove the lead.
Your task is to produce an auditable explanation for the reviewer.

Definitions:

confirmed_geometry:
The source contains concrete evidence for a persistent road or path geometry update.
Examples: new road, relocated road, new junction, new roundabout, new underpass, new bridge, new separate cycle path, changed access, changed entry or exit, mapped traffic island.

plausible_review_signal:
The source contains a plausible TLM signal but not enough confirmed geometry evidence.
Examples: concept, study, programme, funding decision, broad redesign, unclear project description, possible path or road change.

no_geometry_evidence:
The source is mainly maintenance, resurfacing, temporary traffic, markings, noise protection, bus stop adaptation, lighting, or administration without geometry evidence.

unclear:
The text is ambiguous or insufficient.

Rules:

Use only the provided source text.
Do not infer geometry changes that are not stated.
Do not invent locations, objects, or project details.
Write explanation_note and audit_warning in German.
Keep evidence_snippet in the original source wording.
Keep evidence_type as one of the English enum values.
The evidence_snippet must be a short quote or close excerpt from the source text.
If possible, copy the exact wording from the source text.
If the source is review worthy but evidence is weak, use plausible_review_signal.
If no evidence can be found, use no_geometry_evidence and explain why.
Distinguish confirmed geometry from plausible but unconfirmed review signals.

Return only JSON with exactly these keys:

{{
  "evidence_type": "confirmed_geometry | plausible_review_signal | no_geometry_evidence | unclear",
  "explanation_note": "eine kurze deutsche Review-Notiz",
  "evidence_snippet": "ein kurzer Evidenz-Ausschnitt aus dem Quelltext in Originalsprache",
  "geometry_signal": "kurzer deutscher Name des Geometrie- oder Review-Signals, möglichst mit Originalbegriff aus der Quelle",
  "audit_warning": "kurzer deutscher Hinweis, falls die Evidenz schwach, indirekt oder fehlend ist"
}}

Lead metadata:

source_id: {source_id}
title: {title}
thematic_score: {score}
tfidf_actionable_probability: {tfidf}

Source text:

{text}
""".strip()


def load_selected_records(
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
        raise ValueError(f"No leads found for mode={mode}")

    merge_columns = [
        "annotation_id",
        "text_full",
        "change_type",
        "notes",
        "target_actionable",
        "target_strict",
    ]

    available = [column for column in merge_columns if column in records.columns]

    selected = selected.merge(
        records[available],
        on="annotation_id",
        how="left",
        suffixes=("", "_record"),
    )

    if selected["text_full"].isna().any():
        missing = selected[selected["text_full"].isna()]["annotation_id"].tolist()
        raise ValueError(f"Missing text_full for selected records: {missing}")

    return selected


def validate_output(parsed: dict[str, Any], source_text: str) -> dict[str, Any]:
    evidence_type = normalize_text(parsed.get("evidence_type"))

    if evidence_type not in VALID_EVIDENCE_TYPES:
        evidence_type = "unclear"

    evidence_snippet = normalize_text(parsed.get("evidence_snippet"))
    source_norm = source_text.casefold()
    snippet_norm = evidence_snippet.casefold()

    evidence_found = bool(snippet_norm) and snippet_norm in source_norm

    return {
        "evidence_type": evidence_type,
        "explanation_note": normalize_text(parsed.get("explanation_note")),
        "evidence_snippet": evidence_snippet,
        "geometry_signal": normalize_text(parsed.get("geometry_signal")),
        "audit_warning": normalize_text(parsed.get("audit_warning")),
        "evidence_snippet_found_in_source": evidence_found,
        "missing_evidence_snippet": evidence_snippet == "",
        "requires_manual_explanation_check": (
            evidence_type in {"unclear", "no_geometry_evidence"}
            or evidence_snippet == ""
            or not evidence_found
        ),
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_report(records: list[dict[str, Any]], model_id: str, mode: str, top_n: int) -> dict[str, Any]:
    df = pd.DataFrame(records)

    return {
        "model_id": model_id,
        "mode": mode,
        "top_n": int(top_n),
        "records": int(len(df)),
        "parse_success_count": int(df["parse_success"].sum()),
        "parse_success_rate": float(df["parse_success"].mean()) if len(df) else 0.0,
        "evidence_type_counts": df["evidence_type"].value_counts().to_dict(),
        "evidence_snippet_found_in_source_count": int(df["evidence_snippet_found_in_source"].sum()),
        "missing_evidence_snippet_count": int(df["missing_evidence_snippet"].sum()),
        "requires_manual_explanation_check_count": int(df["requires_manual_explanation_check"].sum()),
    }


def build_markdown(report: dict[str, Any], output_dir: Path) -> str:
    lines = [
        "# Generated LLM Explainability Evaluation",
        "",
        "## Scope",
        "",
        "This report evaluates a dedicated explanation prompt for already selected ChangeScout leads.",
        "",
        "The explanation model does not select or remove leads.",
        "",
        "It generates evidence fields for human review.",
        "",
        "## Run",
        "",
        f"* Model: `{report['model_id']}`",
        f"* Mode: `{report['mode']}`",
        f"* Top N: `{report['top_n']}`",
        f"* Records: `{report['records']}`",
        f"* Parse success rate: `{report['parse_success_rate']:.3f}`",
        "",
        "## Evidence type counts",
        "",
        "| Evidence type | Count |",
        "|---|---:|",
    ]

    for key, value in sorted(report["evidence_type_counts"].items()):
        lines.append(f"| {key} | {int(value)} |")

    lines.extend([
        "",
        "## Audit metrics",
        "",
        f"* Evidence snippets found in source: `{report['evidence_snippet_found_in_source_count']}`",
        f"* Missing evidence snippets: `{report['missing_evidence_snippet_count']}`",
        f"* Requires manual explanation check: `{report['requires_manual_explanation_check_count']}`",
        "",
        "## Interpretation",
        "",
        "The dedicated explanation prompt should be judged by auditability, not by classification accuracy.",
        "",
        "A useful explanation must provide a source grounded evidence snippet and distinguish confirmed geometry from plausible review signals.",
        "",
        "Any explanation with missing evidence, unsupported evidence, or no geometry evidence remains marked for manual checking.",
        "",
        "## Output files",
        "",
        f"* `{output_dir / 'llm_explainability_generated.jsonl'}`",
        f"* `{output_dir / 'llm_explainability_generated.csv'}`",
        f"* `{output_dir / 'llm_explainability_generated_report.json'}`",
        f"* `{output_dir / 'llm_explainability_generated_report.md'}`",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM explanations for selected ChangeScout leads.")
    parser.add_argument("--model-id", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--leads", default=str(DEFAULT_LEADS))
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    parser.add_argument("--mode", default="score_or_tfidf")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = load_selected_records(
        leads_path=Path(args.leads),
        records_path=Path(args.records),
        mode=args.mode,
        top_n=args.top_n,
    )

    if args.max_records > 0:
        selected = selected.head(args.max_records).copy()

    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    model.eval()

    records: list[dict[str, Any]] = []

    for index, row in selected.iterrows():
        started = time.time()
        prompt = build_prompt(row)

        messages = [{"role": "user", "content": prompt}]
        input_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][inputs["input_ids"].shape[1] :]
        raw_output = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

        parsed, parse_error = extract_json(raw_output)
        validation = validate_output(parsed, normalize_text(row.get("text_full")))

        record = row.to_dict()
        record.update({
            "model_id": args.model_id,
            "raw_output": raw_output,
            "parse_success": parse_error == "",
            "parse_error": parse_error,
            "runtime_seconds": round(time.time() - started, 3),
            **validation,
        })

        records.append(record)

        print(
            f"{len(records)}/{len(selected)} "
            f"{row['annotation_id']} "
            f"type={record['evidence_type']} "
            f"found={record['evidence_snippet_found_in_source']} "
            f"parse={record['parse_success']}"
        )

    output_jsonl = output_dir / "llm_explainability_generated.jsonl"
    output_csv = output_dir / "llm_explainability_generated.csv"
    output_report_json = output_dir / "llm_explainability_generated_report.json"
    output_report_md = output_dir / "llm_explainability_generated_report.md"

    write_jsonl(output_jsonl, records)
    pd.DataFrame(records).to_csv(output_csv, index=False, encoding="utf-8")

    report = build_report(records, args.model_id, args.mode, args.top_n)

    output_report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    output_report_md.write_text(
        build_markdown(report, output_dir),
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
