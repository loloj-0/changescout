from __future__ import annotations

import argparse
from pathlib import Path

from changescout.config import resolve_active_sources
from changescout.snapshot import write_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="ChangeScout CLI")
    parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to config directory",
    )
    parser.add_argument(
        "--snapshot-dir",
        default="artifacts",
        help="Path to snapshot output directory",
    )
    args = parser.parse_args()

    scope, active_sources = resolve_active_sources(Path(args.config_dir))
    snapshot_path = write_snapshot(args.snapshot_dir, scope, active_sources)

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


if __name__ == "__main__":
    main()