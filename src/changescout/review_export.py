from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

import pandas as pd


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


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


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, float) and pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        if isinstance(value, float) and pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def choose_existing_path(paths: List[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def index_records_by_url(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}

    for record in records:
        url = normalize_text(record.get("url"))
        if url:
            indexed[url] = record

    return indexed


def get_best_available_records(run_dir: Path) -> tuple[Path, List[Dict[str, Any]]]:
    candidates = [
        run_dir / "leads_with_llm_explanations.jsonl",
        run_dir / "leads_with_geoadmin_locations.jsonl",
        run_dir / "leads_with_locations.jsonl",
        run_dir / "leads.jsonl",
    ]

    path = choose_existing_path(candidates)

    if path is None:
        raise FileNotFoundError(f"No lead output found in {run_dir}")

    return path, read_jsonl(path)


def load_auxiliary_indexes(run_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    indexes: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for name, path in {
        "leads": run_dir / "leads.jsonl",
        "local_locations": run_dir / "leads_with_locations.jsonl",
        "geoadmin_locations": run_dir / "leads_with_geoadmin_locations.jsonl",
        "llm_explanations": run_dir / "leads_with_llm_explanations.jsonl",
    }.items():
        indexes[name] = index_records_by_url(read_jsonl(path))

    return indexes


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return ""


def get_record_value(
    main_record: Dict[str, Any],
    indexes: Dict[str, Dict[str, Dict[str, Any]]],
    url: str,
    key: str,
) -> Any:
    if key in main_record:
        return main_record.get(key)

    for index in indexes.values():
        record = index.get(url)
        if record and key in record:
            return record.get(key)

    return ""


def compact_preview(text: str, max_length: int) -> str:
    cleaned = " ".join(normalize_text(text).split())

    if max_length <= 0 or len(cleaned) <= max_length:
        return cleaned

    return cleaned[: max_length - 1].rstrip() + "…"


def flatten_location_hints(value: Any) -> str:
    if not isinstance(value, list):
        return ""

    names: list[str] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        name = normalize_text(item.get("name"))
        hint_type = normalize_text(item.get("hint_type"))
        canton = normalize_text(item.get("canton"))

        label = name
        if canton:
            label = f"{label} ({canton})"
        if hint_type:
            label = f"{label} [{hint_type}]"

        if label:
            names.append(label)

    return "; ".join(names)


def flatten_geoadmin_hints(value: Any, max_items: int = 5) -> str:
    if not isinstance(value, list):
        return ""

    names: list[str] = []

    for item in value[:max_items]:
        if not isinstance(item, dict):
            continue

        name = normalize_text(item.get("name"))
        origin = normalize_text(item.get("origin"))
        object_type = normalize_text(item.get("object_type"))

        label = name
        details = [part for part in [origin, object_type] if part]
        if details:
            label = f"{label} [{' / '.join(details)}]"

        if label:
            names.append(label)

    return "; ".join(names)


def build_review_row(
    record: Dict[str, Any],
    indexes: Dict[str, Dict[str, Dict[str, Any]]],
    max_preview_length: int,
) -> Dict[str, Any]:
    url = normalize_text(record.get("url"))

    clean_text = first_non_empty(
        get_record_value(record, indexes, url, "text_preview"),
        get_record_value(record, indexes, url, "clean_text"),
        get_record_value(record, indexes, url, "text_full"),
        get_record_value(record, indexes, url, "preview"),
    )

    location_hints = get_record_value(record, indexes, url, "location_hints")
    geoadmin_hints = get_record_value(record, indexes, url, "geoadmin_location_hints")

    return {
        "rank": safe_int(get_record_value(record, indexes, url, "rank")),
        "title": normalize_text(get_record_value(record, indexes, url, "title")),
        "url": url,
        "source_id": normalize_text(get_record_value(record, indexes, url, "source_id")),
        "selection_mode": normalize_text(get_record_value(record, indexes, url, "selection_mode")),
        "selection_score": safe_float(get_record_value(record, indexes, url, "selection_score")),
        "selection_reason": normalize_text(get_record_value(record, indexes, url, "selection_reason")),
        "thematic_score": safe_float(get_record_value(record, indexes, url, "thematic_score")),
        "tfidf_actionable_probability": safe_float(
            get_record_value(record, indexes, url, "tfidf_actionable_probability")
        ),
        "lead_reason": normalize_text(get_record_value(record, indexes, url, "lead_reason")),
        "location_hint_count": safe_int(
            get_record_value(record, indexes, url, "location_hint_count")
        ),
        "location_hints": flatten_location_hints(location_hints),
        "geoadmin_location_hint_count": safe_int(
            get_record_value(record, indexes, url, "geoadmin_location_hint_count")
        ),
        "geoadmin_top_location_name": normalize_text(
            get_record_value(record, indexes, url, "geoadmin_top_location_name")
        ),
        "geoadmin_best_location_name": normalize_text(
            get_record_value(record, indexes, url, "geoadmin_best_location_name")
        ),
        "geoadmin_best_location_x": safe_float(
            get_record_value(record, indexes, url, "geoadmin_best_location_x")
        ),
        "geoadmin_best_location_y": safe_float(
            get_record_value(record, indexes, url, "geoadmin_best_location_y")
        ),
        "geoadmin_location_hints": flatten_geoadmin_hints(geoadmin_hints),
        "evidence_type": normalize_text(get_record_value(record, indexes, url, "evidence_type")),
        "explanation_note": normalize_text(
            get_record_value(record, indexes, url, "explanation_note")
        ),
        "evidence_snippet": normalize_text(
            get_record_value(record, indexes, url, "evidence_snippet")
        ),
        "geometry_signal": normalize_text(get_record_value(record, indexes, url, "geometry_signal")),
        "audit_warning": normalize_text(get_record_value(record, indexes, url, "audit_warning")),
        "parse_success": get_record_value(record, indexes, url, "parse_success"),
        "evidence_snippet_found_in_source": get_record_value(
            record, indexes, url, "evidence_snippet_found_in_source"
        ),
        "requires_manual_check": get_record_value(
            record, indexes, url, "requires_manual_check"
        )
        or get_record_value(record, indexes, url, "requires_manual_explanation_check"),
        "text_preview": compact_preview(clean_text, max_preview_length),
    }


def sort_review_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row.get("rank") is None,
            row.get("rank") if row.get("rank") is not None else 10**9,
            -(row.get("selection_score") or row.get("thematic_score") or 0.0),
            row.get("title") or "",
            row.get("url") or "",
        ),
    )


def build_markdown_summary(
    run_id: str,
    source_path: Path,
    review_csv_path: Path,
    review_records: List[Dict[str, Any]],
    top_n: int,
) -> str:
    total = len(review_records)
    with_tfidf = sum(
        1 for row in review_records if row.get("tfidf_actionable_probability") is not None
    )
    with_local = sum(1 for row in review_records if row.get("location_hint_count") not in [None, 0])
    with_geoadmin = sum(
        1 for row in review_records if row.get("geoadmin_location_hint_count") not in [None, 0]
    )
    with_explanations = sum(1 for row in review_records if row.get("explanation_note"))

    lines = [
        "# ChangeScout Review Export",
        "",
        "## Scope",
        "",
        f"* Run ID: `{run_id}`",
        f"* Source leads: `{source_path}`",
        f"* Review CSV: `{review_csv_path}`",
        f"* Leads exported: `{total}`",
        "",
        "## Enrichment coverage",
        "",
        f"* Leads with TF IDF probability: `{with_tfidf}`",
        f"* Leads with local location hints: `{with_local}`",
        f"* Leads with GeoAdmin hints: `{with_geoadmin}`",
        f"* Leads with LLM explanations: `{with_explanations}`",
        "",
        "## Top leads",
        "",
        "| Rank | Title | Selection | Score | TF IDF | GeoAdmin | URL |",
        "|---:|---|---|---:|---:|---|---|",
    ]

    for row in review_records[:top_n]:
        rank = row.get("rank") or ""
        title = normalize_text(row.get("title")).replace("|", "\\|")
        selection = normalize_text(row.get("selection_reason")).replace("|", "\\|")
        score = row.get("thematic_score")
        tfidf = row.get("tfidf_actionable_probability")
        geoadmin = normalize_text(row.get("geoadmin_top_location_name")).replace("|", "\\|")
        url = normalize_text(row.get("url"))

        score_text = f"{score:.3f}" if isinstance(score, float) else ""
        tfidf_text = f"{tfidf:.3f}" if isinstance(tfidf, float) else ""

        lines.append(
            f"| {rank} | {title} | {selection} | {score_text} | {tfidf_text} | {geoadmin} | {url} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This export is a review aid.",
            "",
            "A lead is not a confirmed TLM change.",
            "",
            "GeoAdmin coordinates and location hints are not verified project geometries.",
            "",
            "LLM explanations, when present, are audit support and do not replace manual review.",
            "",
        ]
    )

    return "\n".join(lines)


def run_review_export(
    run_dir: Path,
    output_dir: Optional[Path] = None,
    max_preview_length: int = 700,
    top_n: int = 30,
) -> Dict[str, Any]:
    if output_dir is None:
        output_dir = run_dir / "review"

    output_dir.mkdir(parents=True, exist_ok=True)

    source_path, source_records = get_best_available_records(run_dir)
    indexes = load_auxiliary_indexes(run_dir)

    review_rows = [
        build_review_row(
            record=record,
            indexes=indexes,
            max_preview_length=max_preview_length,
        )
        for record in source_records
    ]

    review_rows = sort_review_rows(review_rows)

    review_csv_path = output_dir / "review_leads.csv"
    review_md_path = output_dir / "review_summary.md"
    review_report_path = output_dir / "review_export_report.json"

    pd.DataFrame(review_rows).to_csv(review_csv_path, index=False, encoding="utf-8")

    run_id = run_dir.name

    review_md_path.write_text(
        build_markdown_summary(
            run_id=run_id,
            source_path=source_path,
            review_csv_path=review_csv_path,
            review_records=review_rows,
            top_n=top_n,
        ),
        encoding="utf-8",
    )

    report = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "source_path": str(source_path),
        "output_dir": str(output_dir),
        "review_csv_path": str(review_csv_path),
        "review_markdown_path": str(review_md_path),
        "records": int(len(review_rows)),
        "records_with_tfidf_probability": int(
            sum(
                1
                for row in review_rows
                if row.get("tfidf_actionable_probability") is not None
            )
        ),
        "records_with_local_location_hints": int(
            sum(1 for row in review_rows if row.get("location_hint_count") not in [None, 0])
        ),
        "records_with_geoadmin_hints": int(
            sum(
                1
                for row in review_rows
                if row.get("geoadmin_location_hint_count") not in [None, 0]
            )
        ),
        "records_with_llm_explanations": int(
            sum(1 for row in review_rows if row.get("explanation_note"))
        ),
    }

    write_json(review_report_path, report)

    return report
