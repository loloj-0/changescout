from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
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


def load_filter_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError("filter config must be a YAML mapping")

    return data


def normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""

    return value.casefold().strip()


def contains_any(value: str, patterns: List[str]) -> Optional[str]:
    normalized_value = normalize_text(value)

    for pattern in patterns:
        normalized_pattern = normalize_text(pattern)
        if normalized_pattern and normalized_pattern in normalized_value:
            return pattern

    return None


def build_excluded_record(
    document: Dict[str, Any],
    reason: str,
    matched_rule: Optional[str],
) -> Dict[str, Any]:
    return {
        "document_id": document.get("document_id"),
        "source_id": document.get("source_id"),
        "url": document.get("url"),
        "title": document.get("title"),
        "reason": reason,
        "matched_rule": matched_rule,
        "language": document.get("language"),
        "clean_text_length": document.get("clean_text_length"),
    }


def apply_hard_filter(
    document: Dict[str, Any],
    filter_config: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    hard_exclusion = filter_config.get("hard_exclusion", {})

    title_keywords = hard_exclusion.get("title_keywords", [])
    url_keywords = hard_exclusion.get("url_keywords", [])

    if not isinstance(title_keywords, list):
        raise ValueError("hard_exclusion.title_keywords must be a list")

    if not isinstance(url_keywords, list):
        raise ValueError("hard_exclusion.url_keywords must be a list")

    title = document.get("title", "")
    url = document.get("url", "")

    matched_title_rule = contains_any(title, title_keywords)
    if matched_title_rule:
        excluded = build_excluded_record(
            document=document,
            reason="blacklist_title",
            matched_rule=matched_title_rule,
        )
        return None, excluded

    matched_url_rule = contains_any(url, url_keywords)
    if matched_url_rule:
        excluded = build_excluded_record(
            document=document,
            reason="blacklist_url",
            matched_rule=matched_url_rule,
        )
        return None, excluded

    return document, None


def compute_signals(
    document: Dict[str, Any],
    filter_config: Dict[str, Any],
) -> Dict[str, Any]:
    signals_config = filter_config.get("signals", {})

    structural_keywords = signals_config.get("structural_change_keywords", [])
    soft_keywords = signals_config.get("soft_change_keywords", [])
    min_text_length = signals_config.get("min_text_length", 0)

    clean_text = normalize_text(document.get("clean_text", ""))
    title = normalize_text(document.get("title", ""))
    combined_text = f"{title} {clean_text}"

    structural_hits = [
        keyword for keyword in structural_keywords
        if normalize_text(keyword) in combined_text
    ]

    soft_hits = [
        keyword for keyword in soft_keywords
        if normalize_text(keyword) in combined_text
    ]

    clean_text_length = document.get("clean_text_length", len(clean_text))

    return {
        "clean_text_length": clean_text_length,
        "below_min_text_length": clean_text_length < min_text_length,
        "structural_change_hits": structural_hits,
        "soft_change_hits": soft_hits,
    }


def run_filtering(
    input_path: Path,
    config_path: Path,
    output_path: Path,
    excluded_output_path: Path,
    report_output_path: Path,
) -> Dict[str, Any]:
    filter_config = load_filter_config(config_path)
    documents = load_jsonl(input_path)

    included_documents: List[Dict[str, Any]] = []
    excluded_documents: List[Dict[str, Any]] = []

    for document in documents:
        included, excluded = apply_hard_filter(
            document=document,
            filter_config=filter_config,
        )

        if included is not None:
            included = dict(included)
            included["filter_signals"] = compute_signals(
                document=included,
                filter_config=filter_config,
            )
            included_documents.append(included)

        if excluded is not None:
            excluded_documents.append(excluded)

    exclusion_reasons: Dict[str, int] = {}
    for record in excluded_documents:
        reason = record["reason"]
        exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1

    report = {
        "total_documents": len(documents),
        "included_documents": len(included_documents),
        "excluded_documents": len(excluded_documents),
        "inclusion_rate": len(included_documents) / len(documents) if documents else 0.0,
        "exclusion_reasons": exclusion_reasons,
    }

    write_jsonl(output_path, included_documents)
    write_jsonl(excluded_output_path, excluded_documents)
    write_json(report_output_path, report)

    return report


if __name__ == "__main__":
    report = run_filtering(
        input_path=Path("artifacts/cleaned.jsonl"),
        config_path=Path("config/filter.yaml"),
        output_path=Path("artifacts/filtered.jsonl"),
        excluded_output_path=Path("artifacts/filtered_excluded.jsonl"),
        report_output_path=Path("artifacts/filter_report.json"),
    )

    print("Hard filtering completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))