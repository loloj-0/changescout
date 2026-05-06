from __future__ import annotations

import argparse
import logging
from pathlib import Path

from changescout.config import resolve_active_sources
from changescout.crawling import run_crawling
from changescout.discovery import discover_urls_from_source, write_discovery_jsonl
from changescout.filtering import run_filtering
from changescout.scoring import run_scoring
from changescout.snapshot import write_snapshot
from changescout.pipeline import run_operational_pipeline
from changescout.registry_validation import run_registry_validation

LOGGER = logging.getLogger(__name__)


def run_snapshot(config_dir: Path, snapshot_dir: Path) -> None:
    scope, active_sources = resolve_active_sources(config_dir)
    snapshot_path = write_snapshot(snapshot_dir, scope, active_sources)

    print(f"canton_id={scope.canton_id}")
    print(f"source_registry={scope.source_registry}")
    print(f"active_sources={len(active_sources)}")

    for source in active_sources:
        print(f"source_id={source.source_id}")
        print(f"  base_url={source.base_url}")
        print(f"  crawl_type={source.crawl_type}")
        print(f"  crawl_frequency_hours={source.crawl_frequency_hours}")
        print(f"  active={source.active}")
        if source.include_patterns:
            print("  include_patterns:")
            for pattern in source.include_patterns:
                print(f"    - {pattern}")

    print(f"snapshot_path={snapshot_path}")


def run_discovery(config_dir: Path, output_path: Path) -> None:
    _scope, active_sources = resolve_active_sources(config_dir)

    all_records = []

    for source in active_sources:
        try:
            records = discover_urls_from_source(source)
            all_records.extend(records)
        except Exception as exc:
            LOGGER.error(
                "Discovery failed for source_id=%s error=%s",
                source.source_id,
                exc,
            )

    write_discovery_jsonl(all_records, output_path)
    print(f"discovery_output={output_path}")
    print(f"discovered_records={len(all_records)}")


def run_crawl(
    discovery_input_path: Path,
    output_path: Path,
    html_base_dir: Path,
    run_id: str,
    timeout_seconds: int,
) -> None:
    records = run_crawling(
        discovery_input_path=discovery_input_path,
        output_jsonl_path=output_path,
        html_base_dir=html_base_dir,
        run_id=run_id,
        timeout_seconds=timeout_seconds,
    )

    print(f"crawl_output={output_path}")
    print(f"crawl_records={len(records)}")
    print(f"html_base_dir={html_base_dir}")
    print(f"run_id={run_id}")


def run_filter(
    input_path: Path,
    config_path: Path,
    output_path: Path,
    excluded_output_path: Path,
    report_output_path: Path,
) -> None:
    report = run_filtering(
        input_path=input_path,
        config_path=config_path,
        output_path=output_path,
        excluded_output_path=excluded_output_path,
        report_output_path=report_output_path,
    )

    print(f"filter_output={output_path}")
    print(f"filter_excluded_output={excluded_output_path}")
    print(f"filter_report={report_output_path}")
    print(f"total_documents={report['total_documents']}")
    print(f"included_documents={report['included_documents']}")
    print(f"excluded_documents={report['excluded_documents']}")


def run_score(
    input_path: Path,
    config_path: Path,
    output_path: Path,
    report_output_path: Path,
) -> None:
    report = run_scoring(
        input_path=input_path,
        config_path=config_path,
        output_path=output_path,
        report_output_path=report_output_path,
    )

    print(f"scored_output={output_path}")
    print(f"scoring_report={report_output_path}")
    print(f"total_documents={report['total_documents']}")
    print(f"min_score={report['min_score']}")
    print(f"max_score={report['max_score']}")
    print(f"mean_score={report['mean_score']}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="ChangeScout CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot", help="Resolve active sources and write snapshot")
    snapshot_parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to config directory",
    )
    snapshot_parser.add_argument(
        "--snapshot-dir",
        default="artifacts",
        help="Path to snapshot output directory",
    )

    discovery_parser = subparsers.add_parser("discover", help="Run source discovery and write discovered URLs")
    discovery_parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to config directory",
    )
    discovery_parser.add_argument(
        "--output",
        default="artifacts/discovery.jsonl",
        help="Path to discovery output file",
    )

    crawl_parser = subparsers.add_parser("crawl", help="Run page crawling from discovery output")
    crawl_parser.add_argument(
        "--input",
        default="artifacts/discovery.jsonl",
        help="Path to discovery input file",
    )
    crawl_parser.add_argument(
        "--output",
        default="artifacts/crawl.jsonl",
        help="Path to crawl output file",
    )
    crawl_parser.add_argument(
        "--html-base-dir",
        default="data/crawling",
        help="Base directory for stored raw HTML files",
    )
    crawl_parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier used for HTML storage layout",
    )
    crawl_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
        help="HTTP timeout in seconds",
    )

    filter_parser = subparsers.add_parser("filter", help="Run hard off topic filtering")
    filter_parser.add_argument(
        "--input",
        default="artifacts/cleaned.jsonl",
        help="Path to cleaned input file",
    )
    filter_parser.add_argument(
        "--config",
        default="config/filter.yaml",
        help="Path to filter config file",
    )
    filter_parser.add_argument(
        "--output",
        default="artifacts/filtered.jsonl",
        help="Path to filtered output file",
    )
    filter_parser.add_argument(
        "--excluded-output",
        default="artifacts/filtered_excluded.jsonl",
        help="Path to excluded output file",
    )
    filter_parser.add_argument(
        "--report-output",
        default="artifacts/filter_report.json",
        help="Path to filter report file",
    )

    score_parser = subparsers.add_parser("score", help="Run thematic scoring")
    score_parser.add_argument(
        "--input",
        default="artifacts/filtered.jsonl",
        help="Path to filtered input file",
    )
    score_parser.add_argument(
        "--config",
        default="config/scoring.yaml",
        help="Path to scoring config file",
    )
    score_parser.add_argument(
        "--output",
        default="artifacts/scored.jsonl",
        help="Path to scored output file",
    )
    score_parser.add_argument(
        "--report-output",
        default="artifacts/scoring_report.json",
        help="Path to scoring report file",
    )

    validate_parser = subparsers.add_parser(
        "validate-registry",
        help="Validate a source registry and optionally run discovery smoke test",
    )
    validate_parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to config directory",
    )
    validate_parser.add_argument(
        "--source-registry",
        required=True,
        help="Source registry id, for example be or zh",
    )
    validate_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for validation reports",
    )
    validate_parser.add_argument(
        "--smoke-discovery",
        action="store_true",
        help="Run discovery smoke test after registry validation",
    )
    validate_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
        help="HTTP timeout in seconds for smoke discovery",
    )

    infer_parser = subparsers.add_parser(
        "infer",
        help="Run standard scoped inference preset",
    )
    infer_parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to config directory",
    )
    infer_parser.add_argument(
        "--source-registry",
        required=True,
        help="Source registry id, for example be or zh",
    )
    infer_parser.add_argument(
        "--canton-id",
        required=True,
        help="Canton id stored in the run scope snapshot",
    )
    infer_parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier used for scoped inference outputs",
    )
    infer_parser.add_argument(
        "--output-root",
        default="artifacts/runs",
        help="Root directory for scoped run outputs",
    )
    infer_parser.add_argument(
        "--html-root",
        default="data/crawling",
        help="Root directory for stored raw HTML files",
    )
    infer_parser.add_argument(
        "--tfidf-model-artifact",
        default="data/models/tfidf_actionable/tfidf_actionable_v1",
        help="TF IDF actionable model artifact directory",
    )
    infer_parser.add_argument(
        "--lead-threshold",
        type=float,
        default=0.10,
        help="Thematic score threshold for candidate selection",
    )
    infer_parser.add_argument(
        "--tfidf-threshold",
        type=float,
        default=0.50,
        help="TF IDF actionable probability threshold",
    )
    infer_parser.add_argument(
        "--enable-geoadmin-enrichment",
        action="store_true",
        help="Enable optional GeoAdmin enrichment",
    )
    infer_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
        help="HTTP timeout in seconds",
    )
    infer_parser.add_argument(
        "--preview-length",
        type=int,
        default=500,
        help="Maximum lead text preview length",
    )
    infer_parser.add_argument(
        "--min-text-length",
        type=int,
        default=300,
        help="Minimum cleaned text length",
    )
    infer_parser.add_argument(
        "--allowed-languages",
        nargs="+",
        default=["de"],
        help="Allowed document languages for HTML cleaning",
    )
    infer_parser.add_argument(
        "--location-reference",
        default="data/reference/location_hints_reference.csv",
        help="Path to local location hint reference CSV",
    )
    infer_parser.add_argument(
        "--geoadmin-cache",
        default="data/reference/geoadmin_search_cache.jsonl",
        help="Path to GeoAdmin search cache JSONL",
    )
    infer_parser.add_argument(
        "--geoadmin-max-queries",
        type=int,
        default=3,
        help="Maximum GeoAdmin queries per lead",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run scoped operational pipeline",
    )
    run_parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to config directory",
    )
    run_parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier used for scoped operational outputs",
    )
    run_parser.add_argument(
        "--output-root",
        default="artifacts/runs",
        help="Root directory for scoped run outputs",
    )
    run_parser.add_argument(
        "--html-root",
        default="data/crawling",
        help="Root directory for stored raw HTML files",
    )
    run_parser.add_argument(
        "--source-registry",
        default=None,
        help="Optional source registry override, for example zh or sg",
    )
    run_parser.add_argument(
        "--canton-id",
        default=None,
        help="Optional canton id override stored in the run scope snapshot",
    )
    run_parser.add_argument(
        "--filter-config",
        default="config/filter.yaml",
        help="Path to filter config file",
    )
    run_parser.add_argument(
        "--scoring-config",
        default="config/scoring.yaml",
        help="Path to scoring config file",
    )
    run_parser.add_argument(
        "--lead-threshold",
        type=float,
        default=0.10,
        help="Thematic score threshold for lead generation",
    )
    run_parser.add_argument(
        "--tfidf-threshold",
        type=float,
        default=0.5,
        help="TF IDF actionable probability threshold for hybrid candidate selection",
    )
    run_parser.add_argument(
        "--candidate-selection-mode",
        choices=["score_only", "score_or_tfidf"],
        default="score_only",
        help="Candidate selection mode for operational lead generation",
    )
    run_parser.add_argument(
        "--preview-length",
        type=int,
        default=500,
        help="Maximum lead text preview length",
    )
    run_parser.add_argument(
        "--min-text-length",
        type=int,
        default=300,
        help="Minimum cleaned text length",
    )
    run_parser.add_argument(
        "--allowed-languages",
        nargs="+",
        default=["de"],
        help="Allowed document languages for HTML cleaning",
    )
    run_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
        help="HTTP timeout in seconds",
    )
    run_parser.add_argument(
        "--disable-location-hinting",
        action="store_true",
        help="Disable local location hinting after lead generation",
    )
    run_parser.add_argument(
        "--location-reference",
        default="data/reference/location_hints_reference.csv",
        help="Path to local location hint reference CSV",
    )
    run_parser.add_argument(
        "--enable-geoadmin-enrichment",
        action="store_true",
        help="Enable optional GeoAdmin enrichment after local location hinting",
    )
    run_parser.add_argument(
        "--geoadmin-cache",
        default="data/reference/geoadmin_search_cache.jsonl",
        help="Path to GeoAdmin search cache JSONL",
    )
    run_parser.add_argument(
        "--geoadmin-max-queries",
        type=int,
        default=3,
        help="Maximum GeoAdmin queries per lead",
    )
    run_parser.add_argument(
        "--tfidf-model-artifact",
        default=None,
        help="Optional TF IDF actionable model artifact directory",
    )

    args = parser.parse_args()

    if args.command == "run":
        result = run_operational_pipeline(
            config_dir=Path(args.config_dir),
            run_id=args.run_id,
            output_root=Path(args.output_root),
            html_root=Path(args.html_root),
            source_registry=args.source_registry,
            canton_id=args.canton_id,
            filter_config_path=Path(args.filter_config),
            scoring_config_path=Path(args.scoring_config),
            lead_threshold=args.lead_threshold,
            tfidf_threshold=args.tfidf_threshold,
            candidate_selection_mode=args.candidate_selection_mode,
            preview_length=args.preview_length,
            min_text_length=args.min_text_length,
            allowed_languages=args.allowed_languages,
            timeout_seconds=args.timeout_seconds,
            enable_location_hinting=not args.disable_location_hinting,
            enable_geoadmin_enrichment=args.enable_geoadmin_enrichment,
            location_reference_path=Path(args.location_reference),
            geoadmin_cache_path=Path(args.geoadmin_cache),
            geoadmin_max_queries=args.geoadmin_max_queries,
            tfidf_model_artifact_dir=Path(args.tfidf_model_artifact) if args.tfidf_model_artifact else None,
        )
        metadata = result["metadata"]
        print(f"run_id={metadata['run_id']}")
        print(f"status={metadata['status']}")
        print(f"run_dir={metadata['paths']['run_dir']}")
        if args.tfidf_model_artifact:
            print(f"scored_with_tfidf={metadata['paths']['scored_with_tfidf']}")
        print(f"leads_jsonl={metadata['paths']['leads_jsonl']}")
        print(f"leads_csv={metadata['paths']['leads_csv']}")
        print(f"leads_with_locations_jsonl={metadata['paths']['leads_with_locations_jsonl']}")
        print(f"leads_with_locations_csv={metadata['paths']['leads_with_locations_csv']}")
        if args.enable_geoadmin_enrichment:
            print(f"leads_with_geoadmin_locations_jsonl={metadata['paths']['leads_with_geoadmin_locations_jsonl']}")
            print(f"leads_with_geoadmin_locations_csv={metadata['paths']['leads_with_geoadmin_locations_csv']}")
        print(f"metadata={metadata['paths']['metadata']}")
        print(f"log={metadata['paths']['log']}")
    elif args.command == "infer":
        result = run_operational_pipeline(
            config_dir=Path(args.config_dir),
            run_id=args.run_id,
            output_root=Path(args.output_root),
            html_root=Path(args.html_root),
            source_registry=args.source_registry,
            canton_id=args.canton_id,
            filter_config_path=Path("config/filter.yaml"),
            scoring_config_path=Path("config/scoring.yaml"),
            lead_threshold=args.lead_threshold,
            tfidf_threshold=args.tfidf_threshold,
            candidate_selection_mode="score_or_tfidf",
            preview_length=args.preview_length,
            min_text_length=args.min_text_length,
            allowed_languages=args.allowed_languages,
            timeout_seconds=args.timeout_seconds,
            enable_location_hinting=True,
            enable_geoadmin_enrichment=args.enable_geoadmin_enrichment,
            location_reference_path=Path(args.location_reference),
            geoadmin_cache_path=Path(args.geoadmin_cache),
            geoadmin_max_queries=args.geoadmin_max_queries,
            tfidf_model_artifact_dir=Path(args.tfidf_model_artifact),
        )

        metadata = result["metadata"]

        print("preset=standard_inference")
        print(f"run_id={metadata['run_id']}")
        print(f"status={metadata['status']}")
        print(f"run_dir={metadata['paths']['run_dir']}")
        print(f"scored_with_tfidf={metadata['paths']['scored_with_tfidf']}")
        print(f"leads_jsonl={metadata['paths']['leads_jsonl']}")
        print(f"leads_csv={metadata['paths']['leads_csv']}")
        print(f"leads_with_locations_jsonl={metadata['paths']['leads_with_locations_jsonl']}")
        print(f"leads_with_locations_csv={metadata['paths']['leads_with_locations_csv']}")

        if args.enable_geoadmin_enrichment:
            print(f"leads_with_geoadmin_locations_jsonl={metadata['paths']['leads_with_geoadmin_locations_jsonl']}")
            print(f"leads_with_geoadmin_locations_csv={metadata['paths']['leads_with_geoadmin_locations_csv']}")

        print(f"metadata={metadata['paths']['metadata']}")
        print(f"log={metadata['paths']['log']}")

    elif args.command == "validate-registry":
        result = run_registry_validation(
            config_dir=Path(args.config_dir),
            source_registry=args.source_registry,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            smoke_discovery=args.smoke_discovery,
            timeout_seconds=args.timeout_seconds,
        )

        validation = result["validation"]
        smoke = result["smoke_discovery"]

        print(f"registry={validation['registry']}")
        print(f"valid={validation['valid']}")
        print(f"errors={validation.get('error_count', 0)}")
        print(f"warnings={validation.get('warning_count', 0)}")

        if args.output_dir:
            output_dir = Path(args.output_dir)
            print(f"validation_report={output_dir / 'registry_validation_report.json'}")

        if smoke is not None:
            print(f"smoke_status={smoke['status']}")
            print(f"smoke_records={smoke['total_records']}")
            print(f"discovery_output={smoke['discovery_output_path']}")
            if args.output_dir:
                print(f"discovery_report={Path(args.output_dir) / 'discovery_smoke_report.json'}")

        if not validation["valid"]:
            raise SystemExit(1)

        if smoke is not None and smoke["status"] != "success":
            raise SystemExit(1)

    elif args.command == "snapshot":
        run_snapshot(
            config_dir=Path(args.config_dir),
            snapshot_dir=Path(args.snapshot_dir),
        )
    elif args.command == "discover":
        run_discovery(
            config_dir=Path(args.config_dir),
            output_path=Path(args.output),
        )
    elif args.command == "crawl":
        run_crawl(
            discovery_input_path=Path(args.input),
            output_path=Path(args.output),
            html_base_dir=Path(args.html_base_dir),
            run_id=args.run_id,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "filter":
        run_filter(
            input_path=Path(args.input),
            config_path=Path(args.config),
            output_path=Path(args.output),
            excluded_output_path=Path(args.excluded_output),
            report_output_path=Path(args.report_output),
        )
    elif args.command == "score":
        run_score(
            input_path=Path(args.input),
            config_path=Path(args.config),
            output_path=Path(args.output),
            report_output_path=Path(args.report_output),
        )


if __name__ == "__main__":
    main()