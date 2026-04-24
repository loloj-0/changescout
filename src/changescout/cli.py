from __future__ import annotations

import argparse
import logging
from pathlib import Path

from changescout.config import resolve_active_sources
from changescout.crawling import run_crawling
from changescout.discovery import discover_urls_from_source, write_discovery_jsonl
from changescout.snapshot import write_snapshot
from changescout.filtering import run_filtering

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

    args = parser.parse_args()

    if args.command == "snapshot":
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


if __name__ == "__main__":
    main()