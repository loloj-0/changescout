from __future__ import annotations

import argparse
import logging
from pathlib import Path

from changescout.config import resolve_active_sources
from changescout.discovery import discover_urls_from_source, write_discovery_jsonl
from changescout.snapshot import write_snapshot

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


if __name__ == "__main__":
    main()