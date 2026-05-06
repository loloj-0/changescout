from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging
import subprocess

from changescout.config import ScopeConfig, load_scope, load_source_registry
from changescout.crawling import run_crawling
from changescout.decision import classify_document
from changescout.discovery import discover_urls_from_source, write_discovery_jsonl
from changescout.filtering import run_filtering
from changescout.html_cleaning import process_crawl_records
from changescout.leads import run_lead_generation
from changescout.models import DiscoveredUrlRecord
from changescout.scoring import run_scoring, score_documents

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OperationalRunPaths:
    run_id: str
    run_dir: Path
    reports_dir: Path
    metadata_dir: Path
    logs_dir: Path
    html_base_dir: Path
    scope_snapshot_path: Path
    discovery_path: Path
    crawl_path: Path
    cleaned_path: Path
    excluded_path: Path
    filtered_path: Path
    filtered_excluded_path: Path
    scored_path: Path
    leads_jsonl_path: Path
    leads_csv_path: Path
    discovery_report_path: Path
    crawl_report_path: Path
    cleaning_report_path: Path
    filter_report_path: Path
    scoring_report_path: Path
    lead_generation_report_path: Path
    run_metadata_path: Path
    run_log_path: Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_operational_run_paths(
    run_id: str,
    output_root: Path = Path("artifacts/runs"),
    html_root: Path = Path("data/crawling"),
) -> OperationalRunPaths:
    if not run_id:
        raise ValueError("run_id must be a non-empty string")

    run_dir = output_root / run_id
    reports_dir = run_dir / "reports"
    metadata_dir = run_dir / "metadata"
    logs_dir = run_dir / "logs"

    return OperationalRunPaths(
        run_id=run_id,
        run_dir=run_dir,
        reports_dir=reports_dir,
        metadata_dir=metadata_dir,
        logs_dir=logs_dir,
        html_base_dir=html_root,
        scope_snapshot_path=run_dir / "scope_snapshot.json",
        discovery_path=run_dir / "discovery.jsonl",
        crawl_path=run_dir / "crawl.jsonl",
        cleaned_path=run_dir / "cleaned.jsonl",
        excluded_path=run_dir / "excluded.jsonl",
        filtered_path=run_dir / "filtered.jsonl",
        filtered_excluded_path=run_dir / "filtered_excluded.jsonl",
        scored_path=run_dir / "scored.jsonl",
        leads_jsonl_path=run_dir / "leads.jsonl",
        leads_csv_path=run_dir / "leads.csv",
        discovery_report_path=reports_dir / "discovery_report.json",
        crawl_report_path=reports_dir / "crawl_report.json",
        cleaning_report_path=reports_dir / "cleaning_report.json",
        filter_report_path=reports_dir / "filter_report.json",
        scoring_report_path=reports_dir / "scoring_report.json",
        lead_generation_report_path=reports_dir / "lead_generation_report.json",
        run_metadata_path=metadata_dir / "run_metadata.json",
        run_log_path=logs_dir / "run.log",
    )


def ensure_run_directories(paths: OperationalRunPaths) -> None:
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    paths.metadata_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)


def setup_run_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except Exception:
        return ""


def get_git_status_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
        ).strip()
    except Exception:
        return ""


def load_scope_for_run(
    config_dir: Path,
    source_registry: Optional[str] = None,
    canton_id: Optional[str] = None,
) -> ScopeConfig:
    scope = load_scope(config_dir / "scope.yaml")

    if source_registry is None and canton_id is None:
        return scope

    return ScopeConfig(
        version=scope.version,
        canton_id=canton_id or scope.canton_id,
        languages=scope.languages,
        time_window_days=scope.time_window_days,
        source_registry=source_registry or scope.source_registry,
        source_policy=scope.source_policy,
    )


def resolve_sources_for_run(
    config_dir: Path,
    source_registry: Optional[str] = None,
    canton_id: Optional[str] = None,
) -> tuple[ScopeConfig, list[Any]]:
    scope = load_scope_for_run(
        config_dir=config_dir,
        source_registry=source_registry,
        canton_id=canton_id,
    )
    registry_path = config_dir / "sources" / f"{scope.source_registry}.yaml"
    sources = load_source_registry(registry_path)
    active_sources = [source for source in sources if source.active]

    return scope, active_sources


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_scope_snapshot(
    path: Path,
    scope: ScopeConfig,
    active_sources: list[Any],
) -> None:
    snapshot = {
        "created_at": utc_now_iso(),
        "scope": asdict(scope),
        "active_sources": [asdict(source) for source in active_sources],
    }
    write_json(path, snapshot)


def write_run_metadata(
    paths: OperationalRunPaths,
    status: str,
    scope: Optional[ScopeConfig] = None,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = {
        "run_id": paths.run_id,
        "status": status,
        "started_at": started_at,
        "updated_at": utc_now_iso(),
        "ended_at": ended_at or "",
        "error": error or "",
        "git_commit": get_git_commit(),
        "git_status_short": get_git_status_short(),
        "scope": asdict(scope) if scope is not None else None,
        "paths": {
            "run_dir": str(paths.run_dir),
            "scope_snapshot": str(paths.scope_snapshot_path),
            "discovery": str(paths.discovery_path),
            "crawl": str(paths.crawl_path),
            "cleaned": str(paths.cleaned_path),
            "excluded": str(paths.excluded_path),
            "filtered": str(paths.filtered_path),
            "filtered_excluded": str(paths.filtered_excluded_path),
            "scored": str(paths.scored_path),
            "leads_jsonl": str(paths.leads_jsonl_path),
            "leads_csv": str(paths.leads_csv_path),
            "reports_dir": str(paths.reports_dir),
            "metadata": str(paths.run_metadata_path),
            "log": str(paths.run_log_path),
        },
        "report_paths": {
            "discovery": str(paths.discovery_report_path),
            "crawl": str(paths.crawl_report_path),
            "cleaning": str(paths.cleaning_report_path),
            "filter": str(paths.filter_report_path),
            "scoring": str(paths.scoring_report_path),
            "lead_generation": str(paths.lead_generation_report_path),
        },
    }
    write_json(paths.run_metadata_path, metadata)
    return metadata


def build_discovery_report(
    records: list[DiscoveredUrlRecord],
    source_errors: list[dict[str, str]],
) -> Dict[str, Any]:
    by_source: dict[str, int] = {}

    for record in records:
        by_source[record.source_id] = by_source.get(record.source_id, 0) + 1

    return {
        "total_records": len(records),
        "records_by_source": by_source,
        "source_errors": source_errors,
        "failed_sources": len(source_errors),
    }


def run_discovery_for_sources(
    active_sources: list[Any],
    output_path: Path,
    report_path: Path,
) -> Dict[str, Any]:
    all_records: list[DiscoveredUrlRecord] = []
    source_errors: list[dict[str, str]] = []

    for source in active_sources:
        try:
            records = discover_urls_from_source(source)
            all_records.extend(records)
        except Exception as exc:
            LOGGER.exception("Discovery failed source_id=%s", source.source_id)
            source_errors.append(
                {
                    "source_id": source.source_id,
                    "error": str(exc),
                }
            )

    write_discovery_jsonl(all_records, output_path)

    report = build_discovery_report(
        records=all_records,
        source_errors=source_errors,
    )
    write_json(report_path, report)

    return report


def build_crawl_report(crawl_records: list[Any]) -> Dict[str, Any]:
    status_codes: dict[str, int] = {}
    error_count = 0

    for record in crawl_records:
        status_key = str(record.status_code)
        status_codes[status_key] = status_codes.get(status_key, 0) + 1

        if record.error:
            error_count += 1

    return {
        "total_records": len(crawl_records),
        "error_records": error_count,
        "success_records": len(crawl_records) - error_count,
        "status_codes": status_codes,
    }


def run_operational_pipeline(
    config_dir: Path,
    run_id: str,
    output_root: Path = Path("artifacts/runs"),
    html_root: Path = Path("data/crawling"),
    source_registry: Optional[str] = None,
    canton_id: Optional[str] = None,
    filter_config_path: Path = Path("config/filter.yaml"),
    scoring_config_path: Path = Path("config/scoring.yaml"),
    lead_threshold: float = 0.10,
    preview_length: int = 500,
    min_text_length: int = 300,
    allowed_languages: Optional[list[str]] = None,
    timeout_seconds: int = 10,
) -> Dict[str, Any]:
    if allowed_languages is None:
        allowed_languages = ["de"]

    paths = build_operational_run_paths(
        run_id=run_id,
        output_root=output_root,
        html_root=html_root,
    )
    ensure_run_directories(paths)
    setup_run_logging(paths.run_log_path)

    started_at = utc_now_iso()
    scope: Optional[ScopeConfig] = None

    try:
        scope, active_sources = resolve_sources_for_run(
            config_dir=config_dir,
            source_registry=source_registry,
            canton_id=canton_id,
        )

        write_run_metadata(
            paths=paths,
            status="running",
            scope=scope,
            started_at=started_at,
        )

        write_scope_snapshot(
            path=paths.scope_snapshot_path,
            scope=scope,
            active_sources=active_sources,
        )

        discovery_report = run_discovery_for_sources(
            active_sources=active_sources,
            output_path=paths.discovery_path,
            report_path=paths.discovery_report_path,
        )

        crawl_records = run_crawling(
            discovery_input_path=paths.discovery_path,
            output_jsonl_path=paths.crawl_path,
            html_base_dir=paths.html_base_dir,
            run_id=paths.run_id,
            timeout_seconds=timeout_seconds,
        )
        crawl_report = build_crawl_report(crawl_records)
        write_json(paths.crawl_report_path, crawl_report)

        cleaning_report = process_crawl_records(
            input_path=str(paths.crawl_path),
            cleaned_output_path=str(paths.cleaned_path),
            excluded_output_path=str(paths.excluded_path),
            report_output_path=str(paths.cleaning_report_path),
            min_text_length=min_text_length,
            allowed_languages=allowed_languages,
        )

        filter_report = run_filtering(
            input_path=paths.cleaned_path,
            config_path=filter_config_path,
            output_path=paths.filtered_path,
            excluded_output_path=paths.filtered_excluded_path,
            report_output_path=paths.filter_report_path,
        )

        scoring_report = run_scoring(
            input_path=paths.filtered_path,
            config_path=scoring_config_path,
            output_path=paths.scored_path,
            report_output_path=paths.scoring_report_path,
        )

        lead_generation_report = run_lead_generation(
            scored_path=paths.scored_path,
            classifier_predictions_path=None,
            output_jsonl_path=paths.leads_jsonl_path,
            output_csv_path=paths.leads_csv_path,
            report_output_path=paths.lead_generation_report_path,
            threshold=lead_threshold,
            preview_length=preview_length,
        )

        ended_at = utc_now_iso()
        metadata = write_run_metadata(
            paths=paths,
            status="success",
            scope=scope,
            started_at=started_at,
            ended_at=ended_at,
        )

        return {
            "metadata": metadata,
            "discovery_report": discovery_report,
            "crawl_report": crawl_report,
            "cleaning_report": cleaning_report,
            "filter_report": filter_report,
            "scoring_report": scoring_report,
            "lead_generation_report": lead_generation_report,
        }

    except Exception as exc:
        LOGGER.exception("Operational pipeline failed")
        write_run_metadata(
            paths=paths,
            status="failed",
            scope=scope,
            started_at=started_at,
            ended_at=utc_now_iso(),
            error=str(exc),
        )
        raise


def run_scoring_and_decision(
    documents: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    scored_documents = score_documents(documents, config)
    return [classify_document(document) for document in scored_documents]
