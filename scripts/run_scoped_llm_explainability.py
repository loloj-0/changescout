from __future__ import annotations

import argparse
import json
from pathlib import Path

from changescout.ml.llm_explainability import DEFAULT_MODEL_ID, run_scoped_llm_explainability


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run optional scoped local LLM explainability for selected ChangeScout leads."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Scoped run directory, for example artifacts/runs/run_001.",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help="Hugging Face model id for local explanation generation.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Optional input leads JSONL. Defaults to best available scoped leads.",
    )
    parser.add_argument(
        "--output-jsonl",
        default=None,
        help="Output JSONL. Defaults to <run-dir>/leads_with_llm_explanations.jsonl.",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Output CSV. Defaults to <run-dir>/leads_with_llm_explanations.csv.",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Report JSON. Defaults to <run-dir>/reports/llm_explainability_report.json.",
    )
    parser.add_argument(
        "--report-md",
        default=None,
        help="Report Markdown. Defaults to <run-dir>/reports/llm_explainability_report.md.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Maximum number of selected leads to explain. 0 means all.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=384,
        help="Maximum generated tokens per lead.",
    )

    args = parser.parse_args()

    report = run_scoped_llm_explainability(
        run_dir=Path(args.run_dir),
        model_id=args.model_id,
        input_path=Path(args.input) if args.input else None,
        output_jsonl_path=Path(args.output_jsonl) if args.output_jsonl else None,
        output_csv_path=Path(args.output_csv) if args.output_csv else None,
        report_json_path=Path(args.report_json) if args.report_json else None,
        report_md_path=Path(args.report_md) if args.report_md else None,
        max_records=args.max_records,
        max_new_tokens=args.max_new_tokens,
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
