from __future__ import annotations

import argparse
import json
from pathlib import Path

from changescout.review_export import run_review_export


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build reviewer facing export package for a scoped ChangeScout run."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Scoped run directory, for example artifacts/runs/run_001.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional review output directory. Defaults to <run-dir>/review.",
    )
    parser.add_argument(
        "--max-preview-length",
        type=int,
        default=700,
        help="Maximum text preview length in review CSV.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="Number of top leads shown in Markdown summary.",
    )

    args = parser.parse_args()

    report = run_review_export(
        run_dir=Path(args.run_dir),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        max_preview_length=args.max_preview_length,
        top_n=args.top_n,
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
