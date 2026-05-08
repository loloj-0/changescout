from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

import pandas as pd


SUPPORTED_SELECTION_MODES = {"score_only", "score_or_tfidf"}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
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


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, float) and pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def get_thematic_score(record: Dict[str, Any]) -> float:
    if "thematic_score" in record:
        return safe_float(record.get("thematic_score"))

    if "score" in record:
        return safe_float(record.get("score"))

    return 0.0


def get_text_preview(record: Dict[str, Any], preview_length: int) -> str:
    text = (
        normalize_text(record.get("clean_text"))
        or normalize_text(record.get("text_full"))
        or normalize_text(record.get("text_preview"))
        or normalize_text(record.get("preview"))
    )

    if preview_length <= 0:
        return text

    return text[:preview_length]


def build_selection_reason(
    mode: str,
    thematic_score: float,
    tfidf_probability: float | None,
    score_threshold: float,
    tfidf_threshold: float,
) -> str:
    reasons: list[str] = []

    if thematic_score >= score_threshold:
        reasons.append(f"thematic_score >= {score_threshold}")

    if mode == "score_or_tfidf":
        if tfidf_probability is None:
            reasons.append("missing TF IDF probability")
        elif tfidf_probability >= tfidf_threshold:
            reasons.append(f"tfidf_actionable_probability >= {tfidf_threshold}")

    if not reasons:
        reasons.append("below selection threshold")

    return "; ".join(reasons)


def select_record(
    mode: str,
    thematic_score: float,
    tfidf_probability: float | None,
    score_threshold: float,
    tfidf_threshold: float,
) -> bool:
    if mode == "score_only":
        return thematic_score >= score_threshold

    if mode == "score_or_tfidf":
        if tfidf_probability is None:
            raise ValueError("score_or_tfidf requires tfidf_actionable_probability")
        return thematic_score >= score_threshold or tfidf_probability >= tfidf_threshold

    raise ValueError(f"Unsupported selection mode: {mode}")


def build_selection_score(
    mode: str,
    thematic_score: float,
    tfidf_probability: float | None,
) -> float:
    if mode == "score_only":
        return thematic_score

    if mode == "score_or_tfidf":
        if tfidf_probability is None:
            raise ValueError("score_or_tfidf requires tfidf_actionable_probability")
        return max(thematic_score, tfidf_probability)

    raise ValueError(f"Unsupported selection mode: {mode}")


def build_lead_record(
    record: Dict[str, Any],
    mode: str,
    rank: int,
    selection_score: float,
    thematic_score: float,
    tfidf_probability: float | None,
    score_threshold: float,
    tfidf_threshold: float,
    preview_length: int,
) -> Dict[str, Any]:
    lead = dict(record)

    lead["selection_mode"] = mode
    lead["selection_score"] = selection_score
    lead["rank"] = rank
    lead["thematic_score"] = thematic_score
    lead["tfidf_actionable_probability"] = tfidf_probability
    lead["selection_reason"] = build_selection_reason(
        mode=mode,
        thematic_score=thematic_score,
        tfidf_probability=tfidf_probability,
        score_threshold=score_threshold,
        tfidf_threshold=tfidf_threshold,
    )
    lead["text_preview"] = get_text_preview(record, preview_length)

    return lead


def run_candidate_selection(
    input_jsonl_path: Path,
    output_jsonl_path: Path,
    output_csv_path: Path,
    report_output_path: Path,
    mode: str,
    score_threshold: float,
    tfidf_threshold: float = 0.5,
    preview_length: int = 500,
) -> Dict[str, Any]:
    if mode not in SUPPORTED_SELECTION_MODES:
        raise ValueError(f"Unsupported selection mode: {mode}")

    records = read_jsonl(input_jsonl_path)

    candidates: list[dict[str, Any]] = []
    missing_tfidf_count = 0

    for record in records:
        thematic_score = get_thematic_score(record)

        tfidf_probability: float | None = None
        if "tfidf_actionable_probability" in record:
            tfidf_probability = safe_float(record.get("tfidf_actionable_probability"))
        elif mode == "score_or_tfidf":
            missing_tfidf_count += 1

        if mode == "score_or_tfidf" and tfidf_probability is None:
            continue

        if not select_record(
            mode=mode,
            thematic_score=thematic_score,
            tfidf_probability=tfidf_probability,
            score_threshold=score_threshold,
            tfidf_threshold=tfidf_threshold,
        ):
            continue

        selection_score = build_selection_score(
            mode=mode,
            thematic_score=thematic_score,
            tfidf_probability=tfidf_probability,
        )

        candidates.append(
            {
                "record": record,
                "selection_score": selection_score,
                "thematic_score": thematic_score,
                "tfidf_probability": tfidf_probability,
                "title": normalize_text(record.get("title")),
                "url": normalize_text(record.get("url")),
            }
        )

    candidates = sorted(
        candidates,
        key=lambda item: (
            -float(item["selection_score"]),
            -float(item["thematic_score"]),
            item["title"],
            item["url"],
        ),
    )

    leads = [
        build_lead_record(
            record=item["record"],
            mode=mode,
            rank=index + 1,
            selection_score=float(item["selection_score"]),
            thematic_score=float(item["thematic_score"]),
            tfidf_probability=item["tfidf_probability"],
            score_threshold=score_threshold,
            tfidf_threshold=tfidf_threshold,
            preview_length=preview_length,
        )
        for index, item in enumerate(candidates)
    ]

    write_jsonl(output_jsonl_path, leads)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(leads).to_csv(output_csv_path, index=False, encoding="utf-8")

    scores = [get_thematic_score(record) for record in records]
    tfidf_values = [
        safe_float(record.get("tfidf_actionable_probability"))
        for record in records
        if "tfidf_actionable_probability" in record
    ]

    report = {
        "input_path": str(input_jsonl_path),
        "output_jsonl_path": str(output_jsonl_path),
        "output_csv_path": str(output_csv_path),
        "mode": mode,
        "input_documents": int(len(records)),
        "lead_count": int(len(leads)),
        "score_threshold": float(score_threshold),
        "tfidf_threshold": float(tfidf_threshold),
        "missing_tfidf_probability_count": int(missing_tfidf_count),
        "min_score": float(min(scores)) if scores else None,
        "max_score": float(max(scores)) if scores else None,
        "mean_score": float(sum(scores) / len(scores)) if scores else None,
        "min_tfidf_probability": float(min(tfidf_values)) if tfidf_values else None,
        "max_tfidf_probability": float(max(tfidf_values)) if tfidf_values else None,
        "mean_tfidf_probability": float(sum(tfidf_values) / len(tfidf_values)) if tfidf_values else None,
    }

    write_json(report_output_path, report)

    return report
