from __future__ import annotations

import argparse
import json
from pathlib import Path

from changescout.tfidf_model import train_tfidf_actionable_artifact


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train operational TF IDF actionable model artifact."
    )
    parser.add_argument(
        "--dataset",
        default="data/annotation/evaluation/triage_3class_dataset.csv",
        help="Frozen triage evaluation dataset.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/models/tfidf_actionable/tfidf_actionable_v1",
        help="Output model artifact directory.",
    )
    parser.add_argument(
        "--model-version",
        default="tfidf_actionable_v1",
        help="Model version written into metadata.",
    )
    parser.add_argument(
        "--train-split",
        default="train",
        help="Training split name.",
    )
    parser.add_argument(
        "--test-split",
        default="test",
        help="Test split name used for artifact metrics.",
    )

    args = parser.parse_args()

    metadata = train_tfidf_actionable_artifact(
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output_dir),
        model_version=args.model_version,
        train_split=args.train_split,
        test_split=args.test_split,
    )

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
