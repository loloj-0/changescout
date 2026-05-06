from __future__ import annotations

import argparse
import json
from pathlib import Path

from changescout.inference_qa import run_inference_qa


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build lightweight QA report for a scoped ChangeScout inference run."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Scoped run directory, for example artifacts/runs/run_001.",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Optional output path for QA JSON report.",
    )
    parser.add_argument(
        "--report-md",
        default=None,
        help="Optional output path for QA Markdown report.",
    )

    args = parser.parse_args()

    report = run_inference_qa(
        run_dir=Path(args.run_dir),
        report_json_path=Path(args.report_json) if args.report_json else None,
        report_md_path=Path(args.report_md) if args.report_md else None,
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
