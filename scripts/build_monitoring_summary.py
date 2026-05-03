from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json


ARTIFACTS_DIR = Path("artifacts")
RUNS_DIR = ARTIFACTS_DIR / "runs"

DEFAULT_OUTPUT_JSON = ARTIFACTS_DIR / "monitoring_summary.json"
DEFAULT_OUTPUT_MD = ARTIFACTS_DIR / "monitoring_summary.md"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, required: bool = False) -> Optional[Dict[str, Any]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return None

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def find_latest_run_metadata(runs_dir: Path = RUNS_DIR) -> Optional[Path]:
    if not runs_dir.exists():
        return None

    candidates = sorted(
        runs_dir.glob("*/run_metadata.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        return None

    return candidates[0]


def classify_report(report_name: str, path: Path) -> Tuple[str, str]:
    name = report_name.casefold()
    path_text = str(path).casefold()

    if "html_cleaning" in name or "html_cleaning" in path_text:
        return "html_cleaning", "html_cleaning"

    if name.startswith("filter") or "filter_report" in path_text:
        return "filtering", "filtering"

    if name.startswith("scoring") or "scoring_report" in path_text:
        return "scoring", "scoring"

    if "classifier" in name or "classification" in name or "classifier_metrics" in path_text:
        return "classification", "classification"

    if "lead_generation" in name or "lead_generation_report" in path_text:
        return "lead_generation", "lead_generation"

    if "geoadmin" in name or "geoadmin" in path_text:
        return "location_hinting", "geoadmin_location_hinting"

    if "location_hinting" in name or "location_hinting_report" in path_text:
        return "location_hinting", "local_location_hinting"

    if "llm" in name or "llm" in path_text:
        return "llm", "llm"

    return "other", "generic"


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
        "min_retrieval_raw_score": report.get("min_retrieval_raw_score"),
        "max_retrieval_raw_score": report.get("max_retrieval_raw_score"),
        "score_buckets": report.get("score_buckets", {}),
    }


def extract_classification_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    classifier = report.get("classifier", {})
    scoring_baseline = report.get("scoring_baseline", {})
    dataset = report.get("dataset", {})

    if not isinstance(classifier, dict):
        classifier = {}

    if not isinstance(scoring_baseline, dict):
        scoring_baseline = {}

    if not isinstance(dataset, dict):
        dataset = {}

    return {
        "dataset": dataset,
        "precision": classifier.get("precision"),
        "recall": classifier.get("recall"),
        "f1": classifier.get("f1"),
        "true_positive": classifier.get("true_positive"),
        "false_positive": classifier.get("false_positive"),
        "true_negative": classifier.get("true_negative"),
        "false_negative": classifier.get("false_negative"),
        "scoring_baseline": scoring_baseline,
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
    simple_values = {}

    for key, value in report.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            simple_values[key] = value

    return simple_values


def extract_metrics(report: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    if report_type == "html_cleaning":
        return extract_html_cleaning_metrics(report)

    if report_type == "filtering":
        return extract_filtering_metrics(report)

    if report_type == "scoring":
        return extract_scoring_metrics(report)

    if report_type == "classification":
        return extract_classification_metrics(report)

    if report_type == "lead_generation":
        return extract_lead_generation_metrics(report)

    if report_type == "local_location_hinting":
        return extract_local_location_hinting_metrics(report)

    if report_type == "geoadmin_location_hinting":
        return extract_geoadmin_location_hinting_metrics(report)

    return extract_generic_metrics(report)


def get_report_paths_from_run_metadata(run_metadata: Optional[Dict[str, Any]]) -> Dict[str, Path]:
    if not run_metadata:
        return {}

    report_paths = run_metadata.get("report_paths", {})

    if not isinstance(report_paths, dict):
        return {}

    paths = {}

    for name, path_value in report_paths.items():
        if not path_value:
            continue

        name = str(name)

        if name == "monitoring_summary":
            continue

        paths[name] = Path(str(path_value))

    return paths


def add_default_optional_reports(report_paths: Dict[str, Path]) -> Dict[str, Path]:
    enriched = dict(report_paths)

    defaults = {
        "classification": Path("data/annotation/evaluation/baseline_classifier_metrics.json"),
    }

    for name, path in defaults.items():
        if name not in enriched and path.exists():
            enriched[name] = path

    return enriched


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

        if stage not in stages:
            stages[stage] = {}

        stages[stage][report_name] = entry

    return stages


def build_warning_list(stages: Dict[str, Any], run_metadata: Dict[str, Any]) -> List[str]:
    warnings = []

    if run_metadata and run_metadata.get("status") != "success":
        warnings.append("Run status is not success")

    for stage_name, reports in stages.items():
        for report_name, entry in reports.items():
            if not entry.get("exists"):
                warnings.append(f"Missing report: {report_name}")

    lead_reports = stages.get("lead_generation", {})
    for report_name, entry in lead_reports.items():
        lead_count = entry.get("metrics", {}).get("lead_count")
        if lead_count == 0:
            warnings.append(f"Lead count is zero in {report_name}")

    classification_reports = stages.get("classification", {})
    for report_name, entry in classification_reports.items():
        f1 = entry.get("metrics", {}).get("f1")
        if f1 is not None and f1 < 0.5:
            warnings.append(f"Classifier F1 below 0.5 in {report_name}")

    scoring_reports = stages.get("scoring", {})
    for report_name, entry in scoring_reports.items():
        mean_score = entry.get("metrics", {}).get("mean_score")
        if mean_score is not None and mean_score == 0:
            warnings.append(f"Mean thematic score is zero in {report_name}")

    return warnings


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


def build_monitoring_summary(
    run_metadata_path: Optional[Path] = None,
) -> Dict[str, Any]:
    if run_metadata_path is None:
        run_metadata_path = find_latest_run_metadata()

    run_metadata = load_json(run_metadata_path) if run_metadata_path else {}

    if run_metadata is None:
        run_metadata = {}

    report_paths = get_report_paths_from_run_metadata(run_metadata)
    report_paths = add_default_optional_reports(report_paths)

    stages = build_stage_reports(report_paths)

    summary = {
        "created_at": utc_now_iso(),
        "run_metadata_path": str(run_metadata_path) if run_metadata_path else "",
        "run": run_metadata,
        "stage_summary": summarize_stage_counts(stages),
        "stages": stages,
    }

    summary["warnings"] = build_warning_list(
        stages=stages,
        run_metadata=run_metadata,
    )

    return summary


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def format_value(value: Any) -> str:
    if value is None or value == "":
        return "N/A"

    return str(value)


def get_first_report_metrics(
    stages: Dict[str, Any],
    stage_name: str,
    preferred_report_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    reports = stages.get(stage_name, {})

    if preferred_report_names:
        for report_name in preferred_report_names:
            entry = reports.get(report_name)
            if entry and entry.get("exists"):
                metrics = entry.get("metrics", {})
                if isinstance(metrics, dict):
                    return metrics

    for entry in reports.values():
        if entry.get("exists"):
            metrics = entry.get("metrics", {})
            if isinstance(metrics, dict):
                return metrics

    return {}


def build_markdown_summary(summary: Dict[str, Any]) -> str:
    run = summary.get("run", {})
    stages = summary.get("stages", {})
    stage_summary = summary.get("stage_summary", {})
    warnings = summary.get("warnings", [])

    lead = get_first_report_metrics(stages, "lead_generation")
    classifier = get_first_report_metrics(stages, "classification")
    local_hinting = get_first_report_metrics(
        stages,
        "location_hinting",
        preferred_report_names=["local_location_hinting"],
    )
    geoadmin_hinting = get_first_report_metrics(
        stages,
        "location_hinting",
        preferred_report_names=["geoadmin_location_hinting"],
    )

    lines = [
        "# ChangeScout Monitoring Summary",
        "",
        "## Run",
        "",
        f"* Run ID: `{format_value(run.get('run_id'))}`",
        f"* Status: `{format_value(run.get('status'))}`",
        f"* Started at: `{format_value(run.get('started_at'))}`",
        f"* Ended at: `{format_value(run.get('ended_at'))}`",
        f"* GeoAdmin enrichment enabled: `{format_value(run.get('geo_admin_enrichment_enabled'))}`",
        f"* Git commit: `{format_value(run.get('git_commit'))}`",
        "",
        "## Stage reports",
        "",
    ]

    if stage_summary:
        for stage_name, counts in sorted(stage_summary.items()):
            lines.append(
                f"* {stage_name}: "
                f"`{counts.get('reports_existing')}/{counts.get('reports_total')}` reports present"
            )
    else:
        lines.append("* No stage reports found")

    lines.extend(
        [
            "",
            "## Lead generation",
            "",
            f"* Input documents: `{format_value(lead.get('input_documents'))}`",
            f"* Lead count: `{format_value(lead.get('lead_count'))}`",
            f"* Threshold: `{format_value(lead.get('threshold'))}`",
            f"* Mean score: `{format_value(lead.get('mean_score'))}`",
            "",
            "## Classification",
            "",
            f"* Precision: `{format_value(classifier.get('precision'))}`",
            f"* Recall: `{format_value(classifier.get('recall'))}`",
            f"* F1: `{format_value(classifier.get('f1'))}`",
            f"* False positives: `{format_value(classifier.get('false_positive'))}`",
            f"* False negatives: `{format_value(classifier.get('false_negative'))}`",
            "",
            "## Location hinting",
            "",
            f"* Local records with hints: `{format_value(local_hinting.get('records_with_hints'))}`",
            f"* Local total hints: `{format_value(local_hinting.get('total_hints'))}`",
            f"* GeoAdmin records with hints: `{format_value(geoadmin_hinting.get('records_with_geoadmin_hints'))}`",
            f"* GeoAdmin total hints: `{format_value(geoadmin_hinting.get('total_geoadmin_hints'))}`",
            f"* GeoAdmin queries: `{format_value(geoadmin_hinting.get('total_geoadmin_queries'))}`",
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


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    summary = build_monitoring_summary()

    write_json(DEFAULT_OUTPUT_JSON, summary)
    write_markdown(DEFAULT_OUTPUT_MD, build_markdown_summary(summary))

    print("Monitoring summary completed")
    print(f"Wrote JSON summary: {DEFAULT_OUTPUT_JSON}")
    print(f"Wrote Markdown summary: {DEFAULT_OUTPUT_MD}")


if __name__ == "__main__":
    main()