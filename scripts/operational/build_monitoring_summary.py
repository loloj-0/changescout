from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


DEFAULT_RUNS_DIR = Path("artifacts/runs")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, required: bool = False) -> Optional[Dict[str, Any]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return None

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def find_latest_run_metadata(runs_dir: Path = DEFAULT_RUNS_DIR) -> Optional[Path]:
    if not runs_dir.exists():
        return None

    candidates = list(runs_dir.glob("*/metadata/run_metadata.json"))
    candidates.extend(runs_dir.glob("*/run_metadata.json"))

    candidates = sorted(
        candidates,
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        return None

    return candidates[0]


def resolve_run_metadata_path(
    run_id: Optional[str],
    run_metadata_path: Optional[Path],
    runs_dir: Path,
) -> Path:
    if run_metadata_path is not None:
        return run_metadata_path

    if run_id:
        scoped = runs_dir / run_id / "metadata" / "run_metadata.json"
        if scoped.exists():
            return scoped

        legacy = runs_dir / run_id / "run_metadata.json"
        if legacy.exists():
            return legacy

        return scoped

    latest = find_latest_run_metadata(runs_dir)
    if latest is None:
        raise FileNotFoundError(f"No run metadata found under {runs_dir}")

    return latest


def infer_run_dir(run_metadata_path: Path, run_metadata: Dict[str, Any]) -> Path:
    paths = run_metadata.get("paths", {})
    if isinstance(paths, dict) and paths.get("run_dir"):
        return Path(str(paths["run_dir"]))

    if run_metadata_path.parent.name == "metadata":
        return run_metadata_path.parent.parent

    return run_metadata_path.parent


def classify_report(report_name: str, path: Path) -> Tuple[str, str]:
    text = f"{report_name} {path}".casefold()

    if "discovery" in text:
        return "discovery", "discovery"

    if "crawl" in text:
        return "crawling", "crawl"

    if "cleaning" in text or "html_cleaning" in text:
        return "html_cleaning", "html_cleaning"

    if "filter" in text:
        return "filtering", "filtering"

    if "scoring" in text:
        return "scoring", "scoring"

    if "lead_generation" in text:
        return "lead_generation", "lead_generation"

    if "geoadmin" in text:
        return "location_hinting", "geoadmin_location_hinting"

    if "location_hinting" in text:
        return "location_hinting", "local_location_hinting"

    if "monitoring_summary" in text:
        return "monitoring", "monitoring_summary"

    return "other", "generic"


def extract_discovery_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_records": report.get("total_records"),
        "records_by_source": report.get("records_by_source", {}),
        "failed_sources": report.get("failed_sources"),
        "source_errors": report.get("source_errors", []),
    }


def extract_crawl_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_records": report.get("total_records"),
        "success_records": report.get("success_records"),
        "error_records": report.get("error_records"),
        "status_codes": report.get("status_codes", {}),
    }


def extract_html_cleaning_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_documents": report.get("total_documents"),
        "included_documents": report.get("included_documents"),
        "excluded_documents": report.get("excluded_documents"),
        "inclusion_rate": report.get("inclusion_rate"),
        "avg_clean_text_length": report.get("avg_clean_text_length"),
        "exclusion_reasons": report.get("exclusion_reasons", {}),
    }


def extract_filtering_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_documents": report.get("total_documents"),
        "included_documents": report.get("included_documents"),
        "excluded_documents": report.get("excluded_documents"),
        "exclusion_reasons": report.get("exclusion_reasons", {}),
    }


def extract_scoring_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_documents": report.get("total_documents"),
        "min_score": report.get("min_score"),
        "max_score": report.get("max_score"),
        "mean_score": report.get("mean_score"),
        "mean_rule_score": report.get("mean_rule_score"),
        "mean_retrieval_score": report.get("mean_retrieval_score"),
        "score_buckets": report.get("score_buckets", {}),
    }


def extract_lead_generation_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "input_documents": report.get("input_documents"),
        "lead_count": report.get("lead_count"),
        "threshold": report.get("threshold"),
        "min_score": report.get("min_score"),
        "max_score": report.get("max_score"),
        "mean_score": report.get("mean_score"),
    }


def extract_local_location_hinting_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_records": report.get("total_records"),
        "records_with_hints": report.get("records_with_hints"),
        "records_without_hints": report.get("records_without_hints"),
        "total_hints": report.get("total_hints"),
        "hint_type_counts": report.get("hint_type_counts", {}),
    }


def extract_geoadmin_location_hinting_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": report.get("status", "success"),
        "error": report.get("error", ""),
        "total_records": report.get("total_records"),
        "records_with_geoadmin_hints": report.get("records_with_geoadmin_hints"),
        "records_without_geoadmin_hints": report.get("records_without_geoadmin_hints"),
        "total_geoadmin_hints": report.get("total_geoadmin_hints"),
        "total_geoadmin_queries": report.get("total_geoadmin_queries"),
        "total_cache_hits": report.get("total_cache_hits"),
        "total_cache_misses": report.get("total_cache_misses"),
        "origin_counts": report.get("origin_counts", {}),
    }


def extract_generic_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    values = {}

    for key, value in report.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            values[key] = value

    return values


def extract_metrics(report: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    if report_type == "discovery":
        return extract_discovery_metrics(report)

    if report_type == "crawl":
        return extract_crawl_metrics(report)

    if report_type == "html_cleaning":
        return extract_html_cleaning_metrics(report)

    if report_type == "filtering":
        return extract_filtering_metrics(report)

    if report_type == "scoring":
        return extract_scoring_metrics(report)

    if report_type == "lead_generation":
        return extract_lead_generation_metrics(report)

    if report_type == "local_location_hinting":
        return extract_local_location_hinting_metrics(report)

    if report_type == "geoadmin_location_hinting":
        return extract_geoadmin_location_hinting_metrics(report)

    return extract_generic_metrics(report)


def get_report_paths_from_run_metadata(run_metadata: Dict[str, Any]) -> Dict[str, Path]:
    report_paths = run_metadata.get("report_paths", {})

    if not isinstance(report_paths, dict):
        return {}

    paths = {}

    for name, value in report_paths.items():
        if not value:
            continue

        name = str(name)
        if name == "monitoring_summary":
            continue

        paths[name] = Path(str(value))

    return paths


def build_stage_reports(report_paths: Dict[str, Path]) -> Dict[str, Any]:
    stages: Dict[str, Any] = {}

    for report_name, path in sorted(report_paths.items()):
        stage, report_type = classify_report(report_name, path)
        exists = path.exists()
        report = load_json(path) if exists else None

        entry = {
            "report_name": report_name,
            "report_type": report_type,
            "path": str(path),
            "exists": exists,
            "metrics": extract_metrics(report, report_type) if report else {},
        }

        stages.setdefault(stage, {})[report_name] = entry

    return stages


def summarize_stage_counts(stages: Dict[str, Any]) -> Dict[str, Any]:
    summary = {}

    for stage_name, reports in stages.items():
        existing = sum(1 for entry in reports.values() if entry.get("exists"))
        missing = sum(1 for entry in reports.values() if not entry.get("exists"))

        summary[stage_name] = {
            "reports_total": len(reports),
            "reports_existing": existing,
            "reports_missing": missing,
        }

    return summary


def get_scope_value(run_metadata: Dict[str, Any], key: str) -> Any:
    scope = run_metadata.get("scope", {})
    if isinstance(scope, dict):
        return scope.get(key)
    return None


def get_first_metrics(
    stages: Dict[str, Any],
    stage_name: str,
    preferred_report_name: Optional[str] = None,
) -> Dict[str, Any]:
    reports = stages.get(stage_name, {})

    if preferred_report_name and preferred_report_name in reports:
        entry = reports[preferred_report_name]
        if entry.get("exists") and isinstance(entry.get("metrics"), dict):
            return entry["metrics"]

    for entry in reports.values():
        if entry.get("exists") and isinstance(entry.get("metrics"), dict):
            return entry["metrics"]

    return {}


def build_warning_list(stages: Dict[str, Any], run_metadata: Dict[str, Any]) -> list[str]:
    warnings: list[str] = []

    if run_metadata.get("status") != "success":
        warnings.append("Run status is not success")

    for reports in stages.values():
        for report_name, entry in reports.items():
            if not entry.get("exists"):
                warnings.append(f"Missing report: {report_name}")

    discovery = get_first_metrics(stages, "discovery")
    if discovery.get("failed_sources"):
        warnings.append(f"Discovery failed sources: {discovery.get('failed_sources')}")

    crawl = get_first_metrics(stages, "crawling")
    if crawl.get("error_records"):
        warnings.append(f"Crawl error records: {crawl.get('error_records')}")

    leads = get_first_metrics(stages, "lead_generation")
    if leads.get("lead_count") == 0:
        warnings.append("Lead count is zero")

    geoadmin = get_first_metrics(
        stages,
        "location_hinting",
        preferred_report_name="geoadmin_location_hinting",
    )
    if geoadmin.get("status") == "failed_non_blocking":
        warnings.append(f"GeoAdmin enrichment failed non blocking: {geoadmin.get('error')}")

    return warnings


def build_core_summary(run_metadata: Dict[str, Any], stages: Dict[str, Any]) -> Dict[str, Any]:
    discovery = get_first_metrics(stages, "discovery")
    crawl = get_first_metrics(stages, "crawling")
    cleaning = get_first_metrics(stages, "html_cleaning")
    filtering = get_first_metrics(stages, "filtering")
    scoring = get_first_metrics(stages, "scoring")
    leads = get_first_metrics(stages, "lead_generation")
    local_hints = get_first_metrics(
        stages,
        "location_hinting",
        preferred_report_name="local_location_hinting",
    )
    geoadmin_hints = get_first_metrics(
        stages,
        "location_hinting",
        preferred_report_name="geoadmin_location_hinting",
    )

    return {
        "run_id": run_metadata.get("run_id"),
        "status": run_metadata.get("status"),
        "source_registry": get_scope_value(run_metadata, "source_registry"),
        "canton_id": get_scope_value(run_metadata, "canton_id"),
        "started_at": run_metadata.get("started_at"),
        "ended_at": run_metadata.get("ended_at"),
        "discovery_count": discovery.get("total_records"),
        "crawl_total_records": crawl.get("total_records"),
        "crawl_success_records": crawl.get("success_records"),
        "crawl_error_records": crawl.get("error_records"),
        "cleaning_total_documents": cleaning.get("total_documents"),
        "cleaning_included_documents": cleaning.get("included_documents"),
        "cleaning_inclusion_rate": cleaning.get("inclusion_rate"),
        "filter_total_documents": filtering.get("total_documents"),
        "filter_included_documents": filtering.get("included_documents"),
        "scoring_total_documents": scoring.get("total_documents"),
        "scoring_min_score": scoring.get("min_score"),
        "scoring_max_score": scoring.get("max_score"),
        "scoring_mean_score": scoring.get("mean_score"),
        "lead_count": leads.get("lead_count"),
        "local_location_records_with_hints": local_hints.get("records_with_hints"),
        "local_location_total_hints": local_hints.get("total_hints"),
        "geoadmin_records_with_hints": geoadmin_hints.get("records_with_geoadmin_hints"),
        "geoadmin_total_hints": geoadmin_hints.get("total_geoadmin_hints"),
        "geoadmin_total_queries": geoadmin_hints.get("total_geoadmin_queries"),
    }


def build_monitoring_summary(run_metadata_path: Path) -> Dict[str, Any]:
    run_metadata = load_json(run_metadata_path, required=True)
    if run_metadata is None:
        raise ValueError(f"Could not load run metadata: {run_metadata_path}")

    report_paths = get_report_paths_from_run_metadata(run_metadata)
    stages = build_stage_reports(report_paths)

    summary = {
        "created_at": utc_now_iso(),
        "run_metadata_path": str(run_metadata_path),
        "run": run_metadata,
        "core_summary": build_core_summary(run_metadata, stages),
        "stage_summary": summarize_stage_counts(stages),
        "stages": stages,
    }

    summary["warnings"] = build_warning_list(stages, run_metadata)

    return summary


def format_value(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    return str(value)


def build_markdown_summary(summary: Dict[str, Any]) -> str:
    core = summary.get("core_summary", {})
    stage_summary = summary.get("stage_summary", {})
    warnings = summary.get("warnings", [])
    run = summary.get("run", {})
    paths = run.get("paths", {}) if isinstance(run.get("paths"), dict) else {}

    lines = [
        "# ChangeScout Monitoring Summary",
        "",
        "## Run",
        "",
        f"* Run ID: `{format_value(core.get('run_id'))}`",
        f"* Status: `{format_value(core.get('status'))}`",
        f"* Source registry: `{format_value(core.get('source_registry'))}`",
        f"* Canton ID: `{format_value(core.get('canton_id'))}`",
        f"* Started at: `{format_value(core.get('started_at'))}`",
        f"* Ended at: `{format_value(core.get('ended_at'))}`",
        "",
        "## Stage report availability",
        "",
    ]

    if stage_summary:
        for stage_name, counts in sorted(stage_summary.items()):
            lines.append(
                f"* {stage_name}: `{counts.get('reports_existing')}/{counts.get('reports_total')}` reports present"
            )
    else:
        lines.append("* No stage reports found")

    lines.extend(
        [
            "",
            "## Pipeline counts",
            "",
            f"* Discovery records: `{format_value(core.get('discovery_count'))}`",
            f"* Crawl success records: `{format_value(core.get('crawl_success_records'))}`",
            f"* Crawl error records: `{format_value(core.get('crawl_error_records'))}`",
            f"* Cleaning included documents: `{format_value(core.get('cleaning_included_documents'))}`",
            f"* Cleaning inclusion rate: `{format_value(core.get('cleaning_inclusion_rate'))}`",
            f"* Filter included documents: `{format_value(core.get('filter_included_documents'))}`",
            f"* Scored documents: `{format_value(core.get('scoring_total_documents'))}`",
            f"* Lead count: `{format_value(core.get('lead_count'))}`",
            "",
            "## Scoring",
            "",
            f"* Min score: `{format_value(core.get('scoring_min_score'))}`",
            f"* Max score: `{format_value(core.get('scoring_max_score'))}`",
            f"* Mean score: `{format_value(core.get('scoring_mean_score'))}`",
            "",
            "## Location hinting",
            "",
            f"* Local records with hints: `{format_value(core.get('local_location_records_with_hints'))}`",
            f"* Local total hints: `{format_value(core.get('local_location_total_hints'))}`",
            f"* GeoAdmin records with hints: `{format_value(core.get('geoadmin_records_with_hints'))}`",
            f"* GeoAdmin total hints: `{format_value(core.get('geoadmin_total_hints'))}`",
            f"* GeoAdmin queries: `{format_value(core.get('geoadmin_total_queries'))}`",
            "",
            "## Key artifacts",
            "",
            f"* Leads JSONL: `{format_value(paths.get('leads_jsonl'))}`",
            f"* Leads CSV: `{format_value(paths.get('leads_csv'))}`",
            f"* Local enriched leads JSONL: `{format_value(paths.get('leads_with_locations_jsonl'))}`",
            f"* GeoAdmin enriched leads JSONL: `{format_value(paths.get('leads_with_geoadmin_locations_jsonl'))}`",
            f"* Run log: `{format_value(paths.get('log'))}`",
            "",
            "## Warnings",
            "",
        ]
    )

    if warnings:
        for warning in warnings:
            lines.append(f"* {warning}")
    else:
        lines.append("* None")

    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a scoped monitoring summary for an operational ChangeScout run."
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--run-metadata", default=None)
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-md", default=None)

    args = parser.parse_args()

    run_metadata_path = resolve_run_metadata_path(
        run_id=args.run_id,
        run_metadata_path=Path(args.run_metadata) if args.run_metadata else None,
        runs_dir=Path(args.runs_dir),
    )

    summary = build_monitoring_summary(run_metadata_path)
    run_dir = infer_run_dir(run_metadata_path, summary["run"])

    output_json = Path(args.output_json) if args.output_json else run_dir / "monitoring_summary.json"
    output_md = Path(args.output_md) if args.output_md else run_dir / "monitoring_summary.md"

    write_json(output_json, summary)
    write_markdown(output_md, build_markdown_summary(summary))

    print("Monitoring summary completed")
    print(f"Run metadata: {run_metadata_path}")
    print(f"Wrote JSON summary: {output_json}")
    print(f"Wrote Markdown summary: {output_md}")


if __name__ == "__main__":
    main()
