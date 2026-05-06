from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit
import csv
import json
import re
import time


VALID_EVIDENCE_TYPES = {
    "confirmed_geometry",
    "plausible_review_signal",
    "no_geometry_evidence",
    "unclear",
}

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_MAX_SOURCE_CHARS = 6000
DEFAULT_MAX_NEW_TOKENS = 384


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def compact_text(value: Any, max_chars: int = DEFAULT_MAX_SOURCE_CHARS) -> str:
    text = " ".join(normalize_text(value).split())

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip()


def canonicalize_url(value: Any) -> str:
    url = normalize_text(value)

    if not url:
        return ""

    try:
        parts = urlsplit(url)
    except ValueError:
        return url.rstrip("/")

    path = parts.path.rstrip("/") or parts.path

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            parts.query,
            "",
        )
    )


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    records: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_csv(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: List[str] = []
    seen = set()

    for record in records:
        for key in record.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def choose_best_lead_path(run_dir: Path) -> Path:
    candidates = [
        run_dir / "leads_with_geoadmin_locations.jsonl",
        run_dir / "leads_with_locations.jsonl",
        run_dir / "leads.jsonl",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(f"No scoped lead file found in {run_dir}")


def index_records_by_url(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}

    for record in records:
        key = canonicalize_url(record.get("url"))
        if key:
            index[key] = record

    return index


def load_source_text_index(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    for path in [
        run_dir / "scored_with_tfidf.jsonl",
        run_dir / "scored.jsonl",
        run_dir / "filtered.jsonl",
        run_dir / "cleaned.jsonl",
    ]:
        records.extend(read_jsonl(path))

    return index_records_by_url(records)


def get_source_text(
    lead: Dict[str, Any],
    source_index: Dict[str, Dict[str, Any]],
) -> str:
    direct = (
        normalize_text(lead.get("clean_text"))
        or normalize_text(lead.get("text_full"))
        or normalize_text(lead.get("text_preview"))
    )

    if direct:
        return direct

    key = canonicalize_url(lead.get("url"))
    source = source_index.get(key, {})

    return (
        normalize_text(source.get("clean_text"))
        or normalize_text(source.get("text_full"))
        or normalize_text(source.get("text_preview"))
        or normalize_text(source.get("preview"))
    )


def prepare_explainability_records(
    run_dir: Path,
    input_path: Optional[Path] = None,
    max_records: int = 0,
) -> tuple[Path, List[Dict[str, Any]]]:
    lead_path = input_path or choose_best_lead_path(run_dir)
    leads = read_jsonl(lead_path)
    source_index = load_source_text_index(run_dir)

    prepared: List[Dict[str, Any]] = []

    for lead in leads:
        record = dict(lead)
        source_text = get_source_text(record, source_index)
        record["llm_source_text"] = compact_text(source_text)

        if not normalize_text(record.get("text_preview")):
            record["text_preview"] = compact_text(source_text, max_chars=500)

        prepared.append(record)

    if max_records > 0:
        prepared = prepared[:max_records]

    return lead_path, prepared


def extract_json(text: str) -> tuple[Dict[str, Any], str]:
    cleaned = normalize_text(text)

    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?",
            "",
            cleaned.strip(),
            flags=re.IGNORECASE,
        ).strip()
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


def build_prompt(record: Dict[str, Any]) -> str:
    title = normalize_text(record.get("title"))
    source_id = normalize_text(record.get("source_id"))
    score = normalize_text(record.get("thematic_score"))
    tfidf = normalize_text(record.get("tfidf_actionable_probability"))
    selection_reason = normalize_text(record.get("selection_reason"))
    source_text = normalize_text(record.get("llm_source_text"))

    return f"""
You are supporting a human reviewer for ChangeScout.

ChangeScout is a lead prioritization system for possible TLM road and path geometry updates.

The lead has already been selected by deterministic score or TF IDF.
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
selection_reason: {selection_reason}

Source text:

{source_text}
""".strip()


def validate_explanation_output(
    parsed: Dict[str, Any],
    source_text: str,
) -> Dict[str, Any]:
    evidence_type = normalize_text(parsed.get("evidence_type"))

    if evidence_type not in VALID_EVIDENCE_TYPES:
        evidence_type = "unclear"

    evidence_snippet = normalize_text(parsed.get("evidence_snippet"))
    source_norm = normalize_text(source_text).casefold()
    snippet_norm = evidence_snippet.casefold()

    evidence_found = bool(snippet_norm) and snippet_norm in source_norm

    requires_manual_check = (
        evidence_type in {"unclear", "no_geometry_evidence"}
        or evidence_snippet == ""
        or not evidence_found
    )

    return {
        "evidence_type": evidence_type,
        "explanation_note": normalize_text(parsed.get("explanation_note")),
        "evidence_snippet": evidence_snippet,
        "geometry_signal": normalize_text(parsed.get("geometry_signal")),
        "audit_warning": normalize_text(parsed.get("audit_warning")),
        "evidence_snippet_found_in_source": evidence_found,
        "missing_evidence_snippet": evidence_snippet == "",
        "requires_manual_check": requires_manual_check,
        "requires_manual_explanation_check": requires_manual_check,
    }


def load_model_and_tokenizer(model_id: str) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    model.eval()

    return model, tokenizer


def generate_raw_output(
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_new_tokens: int,
) -> str:
    import torch

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
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[1] :]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


def summarize_explanations(
    records: List[Dict[str, Any]],
    model_id: str,
    input_path: Path,
    output_jsonl_path: Path,
) -> Dict[str, Any]:
    evidence_counts = Counter(
        normalize_text(record.get("evidence_type")) or "unclear"
        for record in records
    )

    parse_success_count = sum(1 for record in records if record.get("parse_success") is True)
    evidence_found_count = sum(
        1 for record in records if record.get("evidence_snippet_found_in_source") is True
    )
    missing_snippet_count = sum(
        1 for record in records if record.get("missing_evidence_snippet") is True
    )
    manual_check_count = sum(
        1 for record in records if record.get("requires_manual_check") is True
    )

    return {
        "created_at": utc_now_iso(),
        "model_id": model_id,
        "input_path": str(input_path),
        "output_jsonl_path": str(output_jsonl_path),
        "records": int(len(records)),
        "parse_success_count": int(parse_success_count),
        "parse_success_rate": float(parse_success_count / len(records)) if records else 0.0,
        "evidence_type_counts": dict(evidence_counts),
        "evidence_snippet_found_in_source_count": int(evidence_found_count),
        "missing_evidence_snippet_count": int(missing_snippet_count),
        "requires_manual_check_count": int(manual_check_count),
        "explanation_is_selection_signal": False,
    }


def build_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# ChangeScout Scoped LLM Explainability Report",
        "",
        "## Scope",
        "",
        "This report summarizes LLM explanations for already selected scoped ChangeScout leads.",
        "",
        "The LLM does not select or remove leads.",
        "",
        "The output is review support only.",
        "",
        "## Run",
        "",
        f"* Model: `{report['model_id']}`",
        f"* Input: `{report['input_path']}`",
        f"* Output: `{report['output_jsonl_path']}`",
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

    lines.extend(
        [
            "",
            "## Audit metrics",
            "",
            f"* Evidence snippets found in source: `{report['evidence_snippet_found_in_source_count']}`",
            f"* Missing evidence snippets: `{report['missing_evidence_snippet_count']}`",
            f"* Requires manual check: `{report['requires_manual_check_count']}`",
            "",
            "## Interpretation",
            "",
            "LLM explanations are audit support.",
            "",
            "Weak, unsupported, or unclear explanations are flagged for manual review.",
            "",
            "An LLM output must never remove a selected lead.",
            "",
        ]
    )

    return "\n".join(lines)


def run_scoped_llm_explainability(
    run_dir: Path,
    model_id: str = DEFAULT_MODEL_ID,
    input_path: Optional[Path] = None,
    output_jsonl_path: Optional[Path] = None,
    output_csv_path: Optional[Path] = None,
    report_json_path: Optional[Path] = None,
    report_md_path: Optional[Path] = None,
    max_records: int = 0,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
) -> Dict[str, Any]:
    if output_jsonl_path is None:
        output_jsonl_path = run_dir / "leads_with_llm_explanations.jsonl"

    if output_csv_path is None:
        output_csv_path = run_dir / "leads_with_llm_explanations.csv"

    if report_json_path is None:
        report_json_path = run_dir / "reports" / "llm_explainability_report.json"

    if report_md_path is None:
        report_md_path = run_dir / "reports" / "llm_explainability_report.md"

    selected_input_path, prepared_records = prepare_explainability_records(
        run_dir=run_dir,
        input_path=input_path,
        max_records=max_records,
    )

    model, tokenizer = load_model_and_tokenizer(model_id)

    output_records: List[Dict[str, Any]] = []

    for index, record in enumerate(prepared_records, start=1):
        started = time.time()
        prompt = build_prompt(record)

        try:
            raw_output = generate_raw_output(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt,
                max_new_tokens=max_new_tokens,
            )
            parsed, parse_error = extract_json(raw_output)
            parse_success = parse_error == ""
        except Exception as exc:
            raw_output = ""
            parsed = {}
            parse_error = str(exc)
            parse_success = False

        validation = validate_explanation_output(
            parsed=parsed,
            source_text=normalize_text(record.get("llm_source_text")),
        )

        enriched = dict(record)
        enriched.update(
            {
                "llm_explainability_model_id": model_id,
                "llm_explainability_prompt_version": "scoped_v1",
                "raw_llm_explanation_output": raw_output,
                "parse_success": parse_success,
                "parse_error": parse_error,
                "runtime_seconds": round(time.time() - started, 3),
                "explanation_source": "scoped_local_llm_explainability",
                "explanation_is_selection_signal": False,
                **validation,
            }
        )

        output_records.append(enriched)

        title = normalize_text(record.get("title"))[:80]
        print(
            f"{index}/{len(prepared_records)} "
            f"type={enriched['evidence_type']} "
            f"found={enriched['evidence_snippet_found_in_source']} "
            f"parse={enriched['parse_success']} "
            f"title={title}"
        )

    write_jsonl(output_jsonl_path, output_records)
    write_csv(output_csv_path, output_records)

    report = summarize_explanations(
        records=output_records,
        model_id=model_id,
        input_path=selected_input_path,
        output_jsonl_path=output_jsonl_path,
    )

    write_json(report_json_path, report)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(build_markdown_report(report), encoding="utf-8")

    return report
