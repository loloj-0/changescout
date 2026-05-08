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


VALID_TRIAGE_CLASSES = {
    "confirmed_relevant",
    "needs_review",
    "not_relevant",
}

VALID_CHANGE_TYPES = {
    "topology",
    "geometry",
    "attribute_only",
    "none",
}

REQUIRED_OUTPUT_KEYS = {
    "triage_class",
    "tlm_relevant",
    "review_required",
    "change_type",
    "notes",
    "evidence",
}


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_model_name(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "_")


def get_guideline_prompt_block() -> str:
    return """
You classify official Swiss infrastructure source texts for ChangeScout.

The task is based only on the source text.

Core question:
Would a mapper need to add, remove, split, connect, disconnect, reshape, or redraw a geometry in the TLM road and path network based on this source?

Use exactly one class:

confirmed_relevant:
The source itself contains sufficient evidence for a persistent TLM geometry update.

needs_review:
The source contains plausible TLM geometry signals, but the source does not provide enough evidence for confirmed relevance.

not_relevant:
The source contains no plausible TLM geometry update signal, or only maintenance, surface work, markings, temporary traffic management, administrative content, bus stops, operational changes, or external systems without road geometry effect.

Valid mapping:
confirmed_relevant -> tlm_relevant true, review_required false
needs_review -> tlm_relevant false, review_required true
not_relevant -> tlm_relevant false, review_required false

The combination tlm_relevant true and review_required true is invalid.

Confirmed TLM geometry triggers:
new road, new path, removed road or path, changed road alignment, road relocation, rerouting, bypass, new access road, new connection, new or changed junction, new roundabout, roundabout replacing an intersection, changed motorway entry or exit, reopened motorway entry or exit with physical works, extended motorway entry or exit lane, new physically separated bike path, new physically separated pedestrian path, new underpass, new overpass, new bridge with geometry effect, bridge with changed alignment, new tunnel, new gallery, new traffic island, new pedestrian crossing island, new Mittelinsel, new Schutzinsel.

False unless concrete geometry evidence is stated:
road resurfacing, deck layer, pavement replacement, drainage, lighting, noise reduction, retaining work, markings, painted bike lane, painted bus lane, bus stop accessibility work, traffic lights, speed limits, signs, temporary detours, temporary closures, temporary traffic management, construction phase routing.

Planning logic:
A concept, study, BGK, forum, synthesis variant, public participation, strategy, or funding decision is not automatically confirmed_relevant.
But do not classify a source as not_relevant only because it contains planning or participation wording.
If the same source contains concrete geometry measures, classify according to those measures.
If concrete future geometry measures are plausible but not confirmed for implementation, classify needs_review.
If concrete geometry implementation is confirmed or strongly implied, classify confirmed_relevant.

Critical rules:
Always judge the whole source text.
Important evidence can occur late in the source.
One confirmed geometry signal is enough to classify the whole source as confirmed_relevant.
Do not infer beyond the text.
Be conservative.
Prefer needs_review over speculative confirmed_relevant.

Notes:
For confirmed_relevant, name the concrete geometry or topology trigger.
For needs_review, name the plausible signal and the missing evidence.
For not_relevant, state why no TLM geometry update is expected.

Change type:
topology means network connectivity, axes, nodes, junctions, roundabouts, entries, exits, access lanes, or connections.
geometry means mapped geometry changes without clear network connectivity change, such as a mapped traffic island.
attribute_only means only an attribute change and no geometric update.
none means no relevant TLM update or insufficient evidence.
For needs_review, use change_type none unless the source clearly confirms the future change type.
""".strip()


def get_output_contract() -> str:
    return """
Return exactly one JSON object.
The first character of your answer must be {.
The last character of your answer must be }.
Do not use Markdown.
Do not wrap the JSON in a code block.
Do not return text outside the JSON.
Do not include additional keys.

Required JSON keys:
{
  "triage_class": "confirmed_relevant | needs_review | not_relevant",
  "tlm_relevant": true,
  "review_required": false,
  "change_type": "topology | geometry | attribute_only | none",
  "notes": "short decision reason",
  "evidence": "short exact or near exact evidence from the source text"
}
""".strip()


def build_direct_prompt(title: str, text: str) -> str:
    return f"""
{get_guideline_prompt_block()}

Classify the following source.

{get_output_contract()}

Source title:
{title}

Full source text:
{text}
""".strip()


def build_hierarchical_prompt(title: str, text: str) -> str:
    return f"""
{get_guideline_prompt_block()}

Classify the following source.

Use this internal sequence:
1. Identify concrete geometry triggers in the full source text.
2. If at least one confirmed trigger exists, classify confirmed_relevant.
3. If no confirmed trigger exists, identify plausible but insufficient TLM geometry signals.
4. If such signals exist, classify needs_review.
5. Otherwise classify not_relevant.

Return only the final JSON object.

{get_output_contract()}

Source title:
{title}

Full source text:
{text}
""".strip()


def build_prompt(title: str, text: str, prompt_variant: str) -> str:
    if prompt_variant == "direct":
        return build_direct_prompt(title=title, text=text)

    if prompt_variant == "hierarchical":
        return build_hierarchical_prompt(title=title, text=text)

    raise ValueError(f"Unknown prompt variant: {prompt_variant}")


def extract_json_object(raw_text: str) -> tuple[dict[str, Any] | None, str]:
    stripped = raw_text.strip()

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed, ""
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")

    if start < 0 or end < 0 or end <= start:
        return None, "no_json_object_found"

    candidate = stripped[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as error:
        return None, f"json_decode_error: {error}"

    if not isinstance(parsed, dict):
        return None, "json_is_not_object"

    return parsed, ""


def validate_schema(parsed: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if parsed is None:
        return False, sorted(REQUIRED_OUTPUT_KEYS)

    missing_keys = sorted(key for key in REQUIRED_OUTPUT_KEYS if key not in parsed)
    return len(missing_keys) == 0, missing_keys


def normalize_prediction(parsed: dict[str, Any] | None) -> dict[str, Any]:
    schema_success, missing_keys = validate_schema(parsed)

    if parsed is None:
        return {
            "parse_success": False,
            "schema_success": False,
            "missing_output_keys": ";".join(missing_keys),
            "triage_class": "invalid",
            "tlm_relevant": False,
            "review_required": False,
            "change_type": "none",
            "notes": "",
            "evidence": "",
        }

    triage_class = normalize_text(parsed.get("triage_class", "")).lower()
    change_type = normalize_text(parsed.get("change_type", "")).lower()

    if triage_class not in VALID_TRIAGE_CLASSES:
        triage_class = "invalid"

    if change_type not in VALID_CHANGE_TYPES:
        change_type = "none"

    if triage_class == "confirmed_relevant":
        tlm_relevant = True
        review_required = False
    elif triage_class == "needs_review":
        tlm_relevant = False
        review_required = True
    elif triage_class == "not_relevant":
        tlm_relevant = False
        review_required = False
    else:
        tlm_relevant = False
        review_required = False

    if triage_class == "needs_review" and change_type != "none":
        change_type = "none"

    return {
        "parse_success": triage_class != "invalid",
        "schema_success": schema_success,
        "missing_output_keys": ";".join(missing_keys),
        "triage_class": triage_class,
        "tlm_relevant": tlm_relevant,
        "review_required": review_required,
        "change_type": change_type,
        "notes": normalize_text(parsed.get("notes", "")),
        "evidence": normalize_text(parsed.get("evidence", "")),
    }


def choose_dtype(dtype_arg: str) -> torch.dtype:
    if dtype_arg == "auto":
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
            return torch.bfloat16
        return torch.float16

    if dtype_arg == "bfloat16":
        return torch.bfloat16

    if dtype_arg == "float16":
        return torch.float16

    if dtype_arg == "float32":
        return torch.float32

    raise ValueError(f"Unsupported dtype: {dtype_arg}")


def load_model(model_id: str, dtype_arg: str) -> tuple[Any, Any]:
    dtype = choose_dtype(dtype_arg)

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )

    model.eval()

    return tokenizer, model


def build_model_input_text(tokenizer: Any, prompt: str) -> str:
    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    return prompt


def count_input_tokens(tokenizer: Any, model_input_text: str) -> int:
    tokenized = tokenizer(
        model_input_text,
        return_tensors=None,
        add_special_tokens=True,
    )

    return len(tokenized["input_ids"])


def generate_response(
    tokenizer: Any,
    model: Any,
    prompt: str,
    max_new_tokens: int,
) -> tuple[str, int]:
    model_input_text = build_model_input_text(tokenizer, prompt)
    input_token_count = count_input_tokens(tokenizer, model_input_text)

    inputs = tokenizer(
        model_input_text,
        return_tensors="pt",
        truncation=False,
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    raw_output = tokenizer.decode(generated_ids, skip_special_tokens=True)

    return raw_output, input_token_count


def prepare_source_text(text: str, max_input_chars: int) -> tuple[str, bool]:
    if max_input_chars <= 0:
        return text, False

    if len(text) <= max_input_chars:
        return text, False

    return text[:max_input_chars], True


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run local Hugging Face LLM triage on the frozen test split."
    )
    parser.add_argument(
        "--model-id",
        required=True,
        help="Hugging Face model id.",
    )
    parser.add_argument(
        "--input",
        default="data/annotation/evaluation/triage_3class_dataset.csv",
        help="Triage evaluation dataset.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/annotation/evaluation/local_llm",
        help="Output root directory.",
    )
    parser.add_argument(
        "--prompt-variant",
        choices=["direct", "hierarchical"],
        default="direct",
    )
    parser.add_argument(
        "--split",
        default="test",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Optional limit for smoke tests. Use 0 for all records.",
    )
    parser.add_argument(
        "--max-input-chars",
        type=int,
        default=0,
        help="Optional source text character limit. Use 0 to keep the full source text.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=384,
    )
    parser.add_argument(
        "--dtype",
        choices=["auto", "bfloat16", "float16", "float32"],
        default="auto",
    )

    args = parser.parse_args()

    model_safe = safe_model_name(args.model_id)
    output_dir = Path(args.output_dir) / model_safe / args.prompt_variant
    output_path = output_dir / "llm_triage_predictions.jsonl"
    report_path = output_dir / "llm_triage_run_report.json"

    df = pd.read_csv(args.input)
    df = df[df["split"] == args.split].copy()

    if args.max_records and args.max_records > 0:
        df = df.head(args.max_records).copy()

    required_columns = [
        "annotation_id",
        "url",
        "source_id",
        "title",
        "text_full",
        "triage_class",
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    tokenizer, model = load_model(args.model_id, args.dtype)

    records: list[dict[str, Any]] = []
    started_at = time.time()

    for _, row in df.iterrows():
        title = normalize_text(row["title"])
        original_text = normalize_text(row["text_full"])
        text, text_was_truncated = prepare_source_text(
            text=original_text,
            max_input_chars=args.max_input_chars,
        )

        prompt = build_prompt(
            title=title,
            text=text,
            prompt_variant=args.prompt_variant,
        )

        item_started = time.time()

        raw_output, input_token_count = generate_response(
            tokenizer=tokenizer,
            model=model,
            prompt=prompt,
            max_new_tokens=args.max_new_tokens,
        )

        parsed, parse_error = extract_json_object(raw_output)
        normalized = normalize_prediction(parsed)

        record = {
            "model_id": args.model_id,
            "prompt_variant": args.prompt_variant,
            "annotation_id": normalize_text(row["annotation_id"]),
            "url": normalize_text(row["url"]),
            "source_id": normalize_text(row["source_id"]),
            "title": title,
            "text_length_chars": len(original_text),
            "prompt_text_length_chars": len(text),
            "text_was_truncated": text_was_truncated,
            "input_token_count": input_token_count,
            "gold_triage_class": normalize_text(row["triage_class"]),
            "gold_change_type": normalize_text(row.get("change_type", "")),
            "gold_notes": normalize_text(row.get("notes", "")),
            "raw_output": raw_output,
            "parse_error": parse_error,
            "runtime_seconds": round(time.time() - item_started, 3),
            **normalized,
        }

        records.append(record)

        print(
            f"{len(records)}/{len(df)}",
            record["annotation_id"],
            "tokens=" + str(record["input_token_count"]),
            "truncated=" + str(record["text_was_truncated"]),
            "gold=" + record["gold_triage_class"],
            "pred=" + record["triage_class"],
            "parse=" + str(record["parse_success"]),
            "schema=" + str(record["schema_success"]),
            flush=True,
        )

    write_jsonl(output_path, records)

    parse_success_count = sum(1 for record in records if record["parse_success"])
    schema_success_count = sum(1 for record in records if record["schema_success"])
    truncated_count = sum(1 for record in records if record["text_was_truncated"])
    missing_evidence_count = sum(1 for record in records if not record["evidence"])
    input_token_counts = [int(record["input_token_count"]) for record in records]

    report = {
        "model_id": args.model_id,
        "prompt_variant": args.prompt_variant,
        "input": args.input,
        "split": args.split,
        "records": len(records),
        "max_input_chars": args.max_input_chars,
        "max_new_tokens": args.max_new_tokens,
        "parse_success_count": parse_success_count,
        "parse_success_rate": parse_success_count / len(records) if records else 0.0,
        "schema_success_count": schema_success_count,
        "schema_success_rate": schema_success_count / len(records) if records else 0.0,
        "missing_evidence_count": missing_evidence_count,
        "missing_evidence_rate": missing_evidence_count / len(records) if records else 0.0,
        "truncated_count": truncated_count,
        "truncated_rate": truncated_count / len(records) if records else 0.0,
        "min_input_tokens": min(input_token_counts) if input_token_counts else None,
        "max_input_tokens": max(input_token_counts) if input_token_counts else None,
        "mean_input_tokens": sum(input_token_counts) / len(input_token_counts) if input_token_counts else None,
        "total_runtime_seconds": round(time.time() - started_at, 3),
        "output_path": str(output_path),
    }

    write_json(report_path, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
