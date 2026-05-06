from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit
import json

import pandas as pd


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        return {}

    return data


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    records: List[Dict[str, Any]] = []

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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    return str(value).strip()


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


def choose_best_lead_path(run_dir: Path) -> Optional[Path]:
    candidates = [
        run_dir / "leads_with_llm_explanations.jsonl",
        run_dir / "leads_with_geoadmin_locations.jsonl",
        run_dir / "leads_with_locations.jsonl",
        run_dir / "leads.jsonl",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def infer_hybrid_mode(run_metadata: Dict[str, Any], run_dir: Path) -> bool:
    paths = run_metadata.get("paths", {})
    report_paths = run_metadata.get("report_paths", {})

    if isinstance(paths, dict) and normalize_text(paths.get("scored_with_tfidf")):
        if (run_dir / "scored_with_tfidf.jsonl").exists():
            return True

    if isinstance(report_paths, dict) and normalize_text(report_paths.get("tfidf_inference")):
        return True

    return (run_dir / "scored_with_tfidf.jsonl").exists()


def find_duplicate_urls(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for record in records:
        key = canonicalize_url(record.get("url"))
        if not key:
            continue
        grouped.setdefault(key, []).append(record)

    duplicates: List[Dict[str, Any]] = []

    for url, group in grouped.items():
        if len(group) <= 1:
            continue

        duplicates.append(
            {
                "canonical_url": url,
                "count": len(group),
                "titles": sorted(
                    {
                        normalize_text(record.get("title"))
                        for record in group
                        if normalize_text(record.get("title"))
                    }
                ),
                "source_ids": sorted(
                    {
                        normalize_text(record.get("source_id"))
                        for record in group
                        if normalize_text(record.get("source_id"))
                    }
                ),
            }
        )

    return duplicates


def build_warning(code: str, message: str, severity: str = "warning") -> Dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
    }


def build_inference_qa_report(run_dir: Path) -> Dict[str, Any]:
    run_metadata_path = run_dir / "metadata" / "run_metadata.json"
    run_metadata = read_json(run_metadata_path)

    lead_path = choose_best_lead_path(run_dir)
    leads = read_jsonl(lead_path) if lead_path is not None else []

    scored = read_jsonl(run_dir / "scored.jsonl")
    scored_with_tfidf = read_jsonl(run_dir / "scored_with_tfidf.jsonl")
    local_locations = read_jsonl(run_dir / "leads_with_locations.jsonl")
    geoadmin_locations = read_jsonl(run_dir / "leads_with_geoadmin_locations.jsonl")

    hybrid_mode = infer_hybrid_mode(run_metadata, run_dir)

    missing_url_count = sum(1 for record in leads if not normalize_text(record.get("url")))
    missing_title_count = sum(1 for record in leads if not normalize_text(record.get("title")))
    missing_selection_reason_count = sum(
        1 for record in leads if not normalize_text(record.get("selection_reason"))
    )

    missing_tfidf_count = 0
    if hybrid_mode:
        missing_tfidf_count = sum(
            1
            for record in leads
            if "tfidf_actionable_probability" not in record
            or record.get("tfidf_actionable_probability") is None
        )

    empty_text_count = sum(
        1
        for record in leads
        if not normalize_text(record.get("text_preview"))
        and not normalize_text(record.get("clean_text"))
        and not normalize_text(record.get("text_full"))
    )

    duplicate_urls = find_duplicate_urls(leads)

    local_hint_records = sum(
        1
        for record in local_locations
        if int(record.get("location_hint_count") or 0) > 0
    )

    geoadmin_hint_records = sum(
        1
        for record in geoadmin_locations
        if int(record.get("geoadmin_location_hint_count") or 0) > 0
    )

    warnings: List[Dict[str, str]] = []

    if lead_path is None:
        warnings.append(
            build_warning(
                code="missing_lead_output",
                severity="error",
                message="No lead output file found in run directory.",
            )
        )

    if len(leads) == 0:
        warnings.append(
            build_warning(
                code="zero_leads",
                message="Lead output contains zero records.",
            )
        )

    if missing_url_count:
        warnings.append(
            build_warning(
                code="missing_urls",
                severity="error",
                message=f"{missing_url_count} leads have no URL.",
            )
        )

    if missing_title_count:
        warnings.append(
            build_warning(
                code="missing_titles",
                message=f"{missing_title_count} leads have no title.",
            )
        )

    if empty_text_count:
        warnings.append(
            build_warning(
                code="empty_text",
                message=f"{empty_text_count} leads have no text preview or source text.",
            )
        )

    if hybrid_mode and missing_tfidf_count:
        warnings.append(
            build_warning(
                code="missing_tfidf_probability",
                severity="error",
                message=f"{missing_tfidf_count} leads are missing TF IDF probability in hybrid mode.",
            )
        )

    if missing_selection_reason_count:
        warnings.append(
            build_warning(
                code="missing_selection_reason",
                message=f"{missing_selection_reason_count} leads are missing selection_reason.",
            )
        )

    if duplicate_urls:
        warnings.append(
            build_warning(
                code="duplicate_urls",
                message=f"{len(duplicate_urls)} canonical URLs occur multiple times in the selected lead output.",
            )
        )

    error_count = sum(1 for warning in warnings if warning["severity"] == "error")
    warning_count = sum(1 for warning in warnings if warning["severity"] == "warning")

    status = "pass" if error_count == 0 else "fail"

    return {
        "created_at": utc_now_iso(),
        "run_dir": str(run_dir),
        "run_metadata_path": str(run_metadata_path),
        "lead_path": str(lead_path) if lead_path is not None else "",
        "status": status,
        "hybrid_mode_detected": hybrid_mode,
        "counts": {
            "scored_records": len(scored),
            "scored_with_tfidf_records": len(scored_with_tfidf),
            "lead_records": len(leads),
            "local_location_records": len(local_locations),
            "geoadmin_location_records": len(geoadmin_locations),
            "missing_url_count": missing_url_count,
            "missing_title_count": missing_title_count,
            "empty_text_count": empty_text_count,
            "missing_tfidf_probability_count": missing_tfidf_count,
            "missing_selection_reason_count": missing_selection_reason_count,
            "duplicate_url_group_count": len(duplicate_urls),
            "local_hint_records": local_hint_records,
            "geoadmin_hint_records": geoadmin_hint_records,
        },
        "warnings": warnings,
        "error_count": error_count,
        "warning_count": warning_count,
        "duplicate_urls": duplicate_urls[:50],
    }


def build_inference_qa_markdown(report: Dict[str, Any]) -> str:
    counts = report.get("counts", {})
    warnings = report.get("warnings", [])

    lines = [
        "# ChangeScout Inference QA Report",
        "",
        "## Run",
        "",
        f"* Run directory: `{report.get('run_dir', '')}`",
        f"* Lead source: `{report.get('lead_path', '')}`",
        f"* Status: `{report.get('status', '')}`",
        f"* Hybrid mode detected: `{report.get('hybrid_mode_detected', False)}`",
        "",
        "## Counts",
        "",
        f"* Scored records: `{counts.get('scored_records', 0)}`",
        f"* Scored with TF IDF records: `{counts.get('scored_with_tfidf_records', 0)}`",
        f"* Lead records: `{counts.get('lead_records', 0)}`",
        f"* Local location records: `{counts.get('local_location_records', 0)}`",
        f"* GeoAdmin location records: `{counts.get('geoadmin_location_records', 0)}`",
        f"* Missing URLs: `{counts.get('missing_url_count', 0)}`",
        f"* Missing titles: `{counts.get('missing_title_count', 0)}`",
        f"* Empty text records: `{counts.get('empty_text_count', 0)}`",
        f"* Missing TF IDF probabilities: `{counts.get('missing_tfidf_probability_count', 0)}`",
        f"* Missing selection reasons: `{counts.get('missing_selection_reason_count', 0)}`",
        f"* Duplicate URL groups: `{counts.get('duplicate_url_group_count', 0)}`",
        f"* Local hint records: `{counts.get('local_hint_records', 0)}`",
        f"* GeoAdmin hint records: `{counts.get('geoadmin_hint_records', 0)}`",
        "",
        "## Warnings",
        "",
    ]

    if not warnings:
        lines.append("* None")
    else:
        for warning in warnings:
            lines.append(
                f"* `{warning.get('severity')}` `{warning.get('code')}`: {warning.get('message')}"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This QA report is a lightweight sanity check.",
            "",
            "It does not evaluate model quality.",
            "",
            "It does not confirm TLM relevance.",
            "",
        ]
    )

    return "\n".join(lines)


def run_inference_qa(
    run_dir: Path,
    report_json_path: Optional[Path] = None,
    report_md_path: Optional[Path] = None,
) -> Dict[str, Any]:
    if report_json_path is None:
        report_json_path = run_dir / "reports" / "inference_qa_report.json"

    if report_md_path is None:
        report_md_path = run_dir / "reports" / "inference_qa_report.md"

    report = build_inference_qa_report(run_dir)

    write_json(report_json_path, report)
    write_text(report_md_path, build_inference_qa_markdown(report))

    return report
