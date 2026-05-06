from __future__ import annotations

import argparse
import json
from pathlib import Path

from changescout.tfidf_model import apply_tfidf_actionable_artifact


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run TF IDF actionable inference on scored ChangeScout records."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input scored JSONL.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output scored JSONL with TF IDF fields.",
    )
    parser.add_argument(
        "--report-output",
        required=True,
        help="Output inference report JSON.",
    )
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="TF IDF model artifact directory.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Optional actionable threshold override.",
    )

    args = parser.parse_args()

    report = apply_tfidf_actionable_artifact(
        input_jsonl_path=Path(args.input),
        output_jsonl_path=Path(args.output),
        report_output_path=Path(args.report_output),
        artifact_dir=Path(args.artifact_dir),
        threshold=args.threshold,
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
